from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import json
import logging
import pathlib
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

import aioboto3
import httpx
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

from app.core.config import AppSettings, get_settings


logger = logging.getLogger("mindwell.data_sync")


class TherapistSource(Protocol):
    """Interface describing a therapist data source."""

    name: str

    async def fetch(self) -> list[dict[str, Any]]:
        """Return raw therapist payloads."""


@dataclass(slots=True)
class HttpJSONSource:
    """Fetch therapist data from an HTTP JSON endpoint."""

    url: str
    locale: str = "zh-CN"
    name: str = field(default="http-json")
    timeout_seconds: float = field(default=20.0)

    async def fetch(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(self.url)
            response.raise_for_status()
            payload = response.json()

        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict):
            for key in ("results", "items", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    records = value
                    break
            else:
                raise ValueError(f"Unsupported JSON schema for {self.url!r}")
        else:
            raise ValueError(f"Unexpected payload type for {self.url!r}: {type(payload)!r}")

        normalized: list[dict[str, Any]] = []
        for item in records:
            if not isinstance(item, dict):
                logger.debug("Skipping non-dict item from %s: %r", self.name, item)
                continue
            item.setdefault("locale", self.locale)
            normalized.append(item)
        logger.info("Fetched %s therapist entries from %s", len(normalized), self.url)
        return normalized


@dataclass(slots=True)
class LocalFileSource:
    """Load therapist data from a local JSON or CSV file."""

    path: pathlib.Path
    locale: str = "zh-CN"
    name: str = field(default="local-file")

    async def fetch(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            raise FileNotFoundError(f"Therapist source file {self.path} not found.")

        suffix = self.path.suffix.lower()
        if suffix == ".json":
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                records = data.get("therapists") or data.get("data") or data.get("results") or []
            else:
                raise ValueError(f"Unsupported JSON schema in {self.path}")
        elif suffix in {".csv", ".tsv"}:
            delimiter = "\t" if suffix == ".tsv" else ","
            with self.path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle, delimiter=delimiter)
                records = list(reader)
        else:
            raise ValueError(f"Unsupported file format for {self.path}")

        normalized: list[dict[str, Any]] = []
        for row in records:
            if not isinstance(row, dict):
                continue
            row.setdefault("locale", self.locale)
            normalized.append(row)
        logger.info("Loaded %s therapist entries from %s", len(normalized), self.path)
        return normalized


@dataclass(slots=True)
class NormalizedTherapist:
    slug: str
    locale: str
    payload: dict[str, Any]
    therapist_id: str | None = None


@dataclass(slots=True)
class SyncResult:
    total_raw: int = 0
    normalized: int = 0
    written: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SecretMirrorMapping:
    aws_secret_id: str
    key_vault_secret_name: str


@dataclass(slots=True)
class SecretMirrorResult:
    mappings: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class DataSyncAgent:
    """Normalize therapist profiles and publish them to the configured S3 bucket."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        s3_client_factory: Callable[..., AsyncIterator[Any]] | None = None,
        secret_client_factory: Callable[[str], AsyncIterator[tuple[Any, Any]]] | None = None,
    ):
        self._settings = settings
        self._s3_client_factory = s3_client_factory or self._build_s3_client_factory()
        self._secret_client_factory = secret_client_factory or self._build_secret_client_factory()

    def _build_s3_client_factory(self) -> Callable[..., AsyncIterator[Any]]:
        @asynccontextmanager
        async def factory() -> AsyncIterator[Any]:
            client_kwargs: dict[str, Any] = {}
            if self._settings.aws_region:
                client_kwargs["region_name"] = self._settings.aws_region
            if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
                client_kwargs["aws_access_key_id"] = self._settings.aws_access_key_id.get_secret_value()
                client_kwargs["aws_secret_access_key"] = (
                    self._settings.aws_secret_access_key.get_secret_value()
                )
            async with aioboto3.client("s3", **client_kwargs) as client:
                yield client

        return factory

    def _build_secret_client_factory(
        self,
    ) -> Callable[[str], AsyncIterator[tuple[Any, Any]]]:
        def builder(vault_url: str) -> AsyncIterator[tuple[Any, Any]]:
            normalized_url = vault_url.rstrip("/")

            @asynccontextmanager
            async def factory() -> AsyncIterator[tuple[Any, Any]]:
                client_kwargs: dict[str, Any] = {}
                if self._settings.aws_region:
                    client_kwargs["region_name"] = self._settings.aws_region
                if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
                    client_kwargs["aws_access_key_id"] = (
                        self._settings.aws_access_key_id.get_secret_value()
                    )
                    client_kwargs["aws_secret_access_key"] = (
                        self._settings.aws_secret_access_key.get_secret_value()
                    )

                async with aioboto3.client("secretsmanager", **client_kwargs) as secrets_client:
                    credential = DefaultAzureCredential(
                        exclude_interactive_browser_credential=True,
                        exclude_visual_studio_code_credential=True,
                        exclude_powershell_credential=True,
                    )
                    secret_client = SecretClient(vault_url=normalized_url, credential=credential)
                    try:
                        yield secrets_client, secret_client
                    finally:
                        await credential.close()
                        await secret_client.close()

            return factory()

        return builder

    async def run(
        self,
        sources: Iterable[TherapistSource],
        *,
        dry_run: bool = False,
        prefix: str | None = None,
    ) -> SyncResult:
        if not self._settings.s3_therapists_bucket:
            raise RuntimeError("S3_BUCKET_THERAPISTS must be configured to publish therapist profiles.")

        result = SyncResult()
        normalized_records: list[NormalizedTherapist] = []

        source_list = list(sources)

        for source in source_list:
            try:
                records = await source.fetch()
            except Exception as exc:
                logger.exception("Failed to fetch therapists from %s", source.name)
                result.errors.append(f"{source.name}: {exc}")
                continue

            result.total_raw += len(records)
            for raw in records:
                try:
                    normalized = self._normalize_record(raw, source_name=source.name)
                except ValueError as exc:
                    logger.warning("Skipping invalid record from %s: %s", source.name, exc)
                    result.skipped += 1
                    continue

                normalized_records.append(normalized)

        result.normalized = len(normalized_records)
        if dry_run:
            logger.info(
                "Dry-run complete. Normalized %s records from %s sources.",
                result.normalized,
                len(source_list),
            )
            return result

        if not normalized_records:
            logger.info("No normalized therapist records to publish.")
            return result

        key_prefix = prefix or self._settings.therapist_data_s3_prefix or "therapists/"
        written = await self._write_records(normalized_records, key_prefix=key_prefix)
        result.written = written
        return result

    async def _write_records(
        self,
        records: Iterable[NormalizedTherapist],
        *,
        key_prefix: str,
    ) -> int:
        bucket = self._settings.s3_therapists_bucket
        if not bucket:
            return 0

        count = 0
        async with self._s3_client_factory() as client:
            for record in records:
                key = self._build_object_key(record, key_prefix=key_prefix)
                body = json.dumps(
                    {
                        **record.payload,
                        "slug": record.slug,
                        "locale": record.locale,
                        "therapist_id": record.therapist_id,
                        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")

                await client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=body,
                    ContentType="application/json",
                )
                logger.debug("Uploaded %s -> s3://%s/%s", record.slug, bucket, key)
                count += 1

        logger.info("Uploaded %s therapist profiles to s3://%s/%s", count, bucket, key_prefix)
        return count

    def _build_object_key(self, record: NormalizedTherapist, *, key_prefix: str) -> str:
        safe_prefix = key_prefix.rstrip("/")
        filename = f"profile_{record.locale}.json"
        return f"{safe_prefix}/{record.slug}/{filename}"

    def _normalize_record(
        self,
        data: dict[str, Any],
        *,
        source_name: str,
    ) -> NormalizedTherapist:
        slug = self._extract_slug(data)
        if not slug:
            raise ValueError("Missing slug or name.")

        locale = str(data.get("locale") or "zh-CN").strip() or "zh-CN"
        therapist_id = self._extract_identifier(data)
        normalized = {
            "name": data.get("name") or data.get("display_name") or slug.title(),
            "title": data.get("title") or data.get("headline"),
            "biography": data.get("biography") or data.get("bio") or "",
            "specialties": self._ensure_list(data.get("specialties") or data.get("tags")),
            "languages": self._ensure_list(data.get("languages") or ["zh-CN"]),
            "availability": self._ensure_list(data.get("availability")),
            "price_per_session": self._coerce_price(data.get("price_per_session") or data.get("price")),
            "currency": (data.get("currency") or "CNY").upper(),
            "is_recommended": bool(data.get("is_recommended") or data.get("featured")),
            "source": source_name,
        }

        media_url = data.get("profile_image_url") or data.get("avatar") or data.get("photo_url")
        if media_url:
            normalized["profile_image_url"] = str(media_url)

        return NormalizedTherapist(
            slug=slug,
            locale=locale,
            payload=normalized,
            therapist_id=therapist_id,
        )

    def _extract_slug(self, data: dict[str, Any]) -> str:
        slug = str(data.get("slug") or "").strip()
        if slug:
            return slug.lower()

        identifier = data.get("therapist_id") or data.get("id") or data.get("uuid")
        if identifier:
            slug_candidate = str(identifier).strip().replace(" ", "-").lower()
            if slug_candidate:
                return slug_candidate[:64]

        name = str(data.get("name") or "").strip()
        if not name:
            return ""

        cleaned = "".join(ch if ch.isalnum() else "-" for ch in name)
        cleaned = "-".join(filter(None, cleaned.split("-"))).lower()
        return cleaned[:64]

    def _extract_identifier(self, data: dict[str, Any]) -> str | None:
        identifier = data.get("therapist_id") or data.get("id") or data.get("uuid")
        if not identifier:
            return None
        return str(identifier)

    def _ensure_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = [item.strip() for item in value.replace("；", ";").replace("，", ",").split(",")]
            return [part for part in parts if part]
        if isinstance(value, Iterable):
            return [str(item) for item in value if item is not None]
        return []

    def _coerce_price(self, value: Any) -> float | None:
        if value in {None, "", "N/A"}:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            logger.debug("Unable to coerce price value %r", value)
            return None

    def _resolve_key_vault_url(
        self,
        *,
        key_vault_name: str | None,
        key_vault_url: str | None,
    ) -> str:
        if key_vault_url:
            return key_vault_url.rstrip("/")
        if key_vault_name:
            return f"https://{key_vault_name}.vault.azure.net/"
        if self._settings.azure_key_vault_url:
            return self._settings.azure_key_vault_url.rstrip("/")
        if self._settings.azure_key_vault_name:
            return f"https://{self._settings.azure_key_vault_name}.vault.azure.net/"
        raise RuntimeError("AZURE_KEY_VAULT_NAME or AZURE_KEY_VAULT_URL must be configured.")

    async def mirror_secrets(
        self,
        mappings: Iterable[SecretMirrorMapping],
        *,
        key_vault_name: str | None = None,
        key_vault_url: str | None = None,
    ) -> SecretMirrorResult:
        mapping_list = [
            mapping
            for mapping in mappings
            if mapping.aws_secret_id and mapping.key_vault_secret_name
        ]
        result = SecretMirrorResult(mappings=len(mapping_list))
        if not mapping_list:
            logger.info("No secret mappings provided; skipping secret mirroring.")
            return result

        vault_url = self._resolve_key_vault_url(
            key_vault_name=key_vault_name,
            key_vault_url=key_vault_url,
        )

        factory_builder = self._secret_client_factory
        async with factory_builder(vault_url) as (secrets_client, key_vault_client):
            for mapping in mapping_list:
                try:
                    response = await secrets_client.get_secret_value(
                        SecretId=mapping.aws_secret_id,
                    )
                except Exception as exc:  # pragma: no cover - network failure path
                    logger.exception("Failed to fetch AWS secret %s", mapping.aws_secret_id)
                    result.errors.append(f"{mapping.aws_secret_id}: {exc}")
                    continue

                payload = response.get("SecretString")
                if payload is None:
                    binary_blob = response.get("SecretBinary")
                    if binary_blob is None:
                        logger.warning(
                            "Secret %s has no SecretString or SecretBinary; skipping",
                            mapping.aws_secret_id,
                        )
                        result.skipped += 1
                        continue
                    payload = base64.b64encode(binary_blob).decode("utf-8")

                try:
                    await key_vault_client.set_secret(
                        mapping.key_vault_secret_name,
                        payload,
                    )
                except Exception as exc:  # pragma: no cover - Azure failure path
                    logger.exception(
                        "Failed to write secret %s to Key Vault",
                        mapping.key_vault_secret_name,
                    )
                    result.errors.append(f"{mapping.key_vault_secret_name}: {exc}")
                    continue

                logger.info(
                    "Synced %s -> %s",
                    mapping.aws_secret_id,
                    mapping.key_vault_secret_name,
                )
                result.updated += 1

        return result


def _build_sources(args: argparse.Namespace) -> list[TherapistSource]:
    sources: list[TherapistSource] = []
    for source_spec in args.source:
        if source_spec.startswith("http"):
            sources.append(HttpJSONSource(url=source_spec, locale=args.locale))
        else:
            path = pathlib.Path(source_spec).expanduser()
            sources.append(LocalFileSource(path=path, locale=args.locale, name=path.name))
    if not sources:
        raise ValueError("At least one --source must be provided.")
    return sources


def _parse_secret_map_spec(spec: str) -> SecretMirrorMapping:
    if "=" not in spec:
        raise ValueError("Secret map must be provided as awsSecretId=keyVaultSecretName.")
    aws_secret_id, secret_name = spec.split("=", 1)
    aws_secret_id = aws_secret_id.strip()
    secret_name = secret_name.strip()
    if not aws_secret_id or not secret_name:
        raise ValueError("Secret map entries must include both awsSecretId and keyVaultSecretName.")
    return SecretMirrorMapping(aws_secret_id=aws_secret_id, key_vault_secret_name=secret_name)


def _load_secret_map_records(payload: Any) -> list[SecretMirrorMapping]:
    if isinstance(payload, dict):
        candidate = payload.get("mappings") or payload.get("entries") or payload.get("secrets")
        if candidate is None:
            payload = [payload]
        else:
            payload = candidate

    if not isinstance(payload, list):
        raise ValueError("Secret mapping payload must be an array or object with a 'mappings' list.")

    mappings: list[SecretMirrorMapping] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        source = str(item.get("aws_secret_id") or item.get("source") or item.get("id") or "").strip()
        target = str(
            item.get("key_vault_secret_name")
            or item.get("target")
            or item.get("key_vault_name")
            or ""
        ).strip()
        if source and target:
            mappings.append(SecretMirrorMapping(aws_secret_id=source, key_vault_secret_name=target))
    return mappings


def _load_secret_map_file(path: pathlib.Path) -> list[SecretMirrorMapping]:
    content = path.read_text(encoding="utf-8")
    payload = json.loads(content)
    return _load_secret_map_records(payload)


def _load_secret_mappings(args: argparse.Namespace, settings: AppSettings) -> list[SecretMirrorMapping]:
    mappings: list[SecretMirrorMapping] = []
    for spec in args.secret_map:
        mappings.append(_parse_secret_map_spec(spec))

    if args.secret_map_file:
        file_path = pathlib.Path(args.secret_map_file).expanduser()
        if not file_path.exists():
            raise FileNotFoundError(f"Secret map file {file_path} does not exist.")
        mappings.extend(_load_secret_map_file(file_path))

    if not mappings and settings.secret_mirror_mappings:
        try:
            payload = json.loads(settings.secret_mirror_mappings)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "SECRET_MIRROR_MAPPINGS must contain valid JSON describing secret mappings.",
            ) from exc
        mappings.extend(_load_secret_map_records(payload))

    if not mappings:
        raise ValueError(
            "No secret mappings provided. Supply --secret-map, --secret-map-file, or SECRET_MIRROR_MAPPINGS.",
        )

    return mappings


async def _run(
    args: argparse.Namespace,
) -> tuple[SyncResult | None, SecretMirrorResult | None]:
    settings = get_settings()
    agent = DataSyncAgent(settings)
    therapist_result: SyncResult | None = None
    secret_result: SecretMirrorResult | None = None

    if args.mode in {"therapists", "all"}:
        sources = _build_sources(args)
        therapist_result = await agent.run(
            sources,
            dry_run=args.dry_run,
            prefix=args.prefix,
        )

    if args.mode in {"secrets", "all"}:
        mappings = _load_secret_mappings(args, settings)
        secret_result = await agent.mirror_secrets(
            mappings,
            key_vault_name=args.key_vault_name,
            key_vault_url=args.key_vault_url,
        )

    if therapist_result is None and secret_result is None:
        raise RuntimeError("Select at least one mode to run (therapists, secrets, or all).")

    return therapist_result, secret_result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    parser = argparse.ArgumentParser(
        prog="mindwell-data-sync",
        description="Fetch therapist sources and publish normalized profiles to S3.",
    )
    parser.add_argument(
        "--mode",
        choices=("therapists", "secrets", "all"),
        default="therapists",
        help="Control which workflow to run: therapist sync (default), secret mirroring, or both.",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Therapist source (local file path or HTTP endpoint). May be provided multiple times.",
    )
    parser.add_argument(
        "--locale",
        default="zh-CN",
        help="Default locale for therapist records without explicit locale metadata.",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Override the object key prefix (defaults to THERAPIST_DATA_S3_PREFIX or therapists/).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process and normalize inputs without uploading to S3.",
    )
    parser.add_argument(
        "--secret-map",
        action="append",
        default=[],
        help="Secret mapping in the form awsSecretId=keyVaultSecretName. Provide multiple times.",
    )
    parser.add_argument(
        "--secret-map-file",
        default=None,
        help="Path to a JSON file describing secret mappings.",
    )
    parser.add_argument(
        "--key-vault-name",
        default=None,
        help="Override the Azure Key Vault name used for secret mirroring.",
    )
    parser.add_argument(
        "--key-vault-url",
        default=None,
        help="Override the Azure Key Vault URL used for secret mirroring.",
    )

    args = parser.parse_args()
    try:
        therapist_result, secret_result = asyncio.run(_run(args))
    except Exception as exc:  # pragma: no cover - CLI failure path
        logger.exception("Data Sync agent failed: %s", exc)
        raise SystemExit(1) from exc

    if therapist_result:
        logger.info(
            "Data Sync completed: %s raw -> %s normalized -> %s written (skipped=%s).",
            therapist_result.total_raw,
            therapist_result.normalized,
            therapist_result.written,
            therapist_result.skipped,
        )

    if secret_result:
        logger.info(
            "Secret mirroring completed: mappings=%s, updated=%s, skipped=%s, errors=%s.",
            secret_result.mappings,
            secret_result.updated,
            secret_result.skipped,
            len(secret_result.errors),
        )
        for error in secret_result.errors:
            logger.error("Secret mirroring error: %s", error)


if __name__ == "__main__":
    main()
