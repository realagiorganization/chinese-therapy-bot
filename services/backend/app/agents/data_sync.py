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
from pathlib import Path
from typing import Any, Literal, Protocol, Sequence

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


SecretMirrorStatus = Literal["updated", "skipped", "error"]


@dataclass(slots=True)
class SecretMirrorMapping:
    """Mapping from an AWS Secrets Manager secret to an Azure Key Vault secret."""

    source_secret_id: str
    target_secret_name: str


@dataclass(slots=True)
class SecretMirrorResult:
    """Outcome of mirroring a single secret."""

    source_secret_id: str
    target_secret_name: str
    status: SecretMirrorStatus
    message: str
    version_id: str | None = None


@dataclass(slots=True)
class DataSyncOutcome:
    """Aggregate result of the data sync agent run."""

    therapist_result: SyncResult | None = None
    secret_results: list[SecretMirrorResult] = field(default_factory=list)


class DataSyncAgent:
    """Normalize therapist profiles and publish them to the configured S3 bucket."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        s3_client_factory: Callable[..., AsyncIterator[Any]] | None = None,
        secrets_manager_factory: Callable[..., AsyncIterator[Any]] | None = None,
        key_vault_client_factory: Callable[..., AsyncIterator[SecretClient]] | None = None,
    ):
        self._settings = settings
        if not settings.s3_therapists_bucket:
            logger.warning(
                "S3_BUCKET_THERAPISTS is not configured; therapist profile uploads will be skipped."
            )
        self._s3_client_factory = s3_client_factory or self._build_s3_client_factory()
        self._secrets_manager_factory = secrets_manager_factory
        self._key_vault_client_factory = key_vault_client_factory
        self._metrics_path = (
            Path(settings.data_sync_metrics_path).expanduser()
            if settings.data_sync_metrics_path
            else None
        )

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

    def _ensure_secrets_manager_factory(self) -> Callable[..., AsyncIterator[Any]]:
        if self._secrets_manager_factory is None:
            self._secrets_manager_factory = self._build_secrets_manager_factory()
        return self._secrets_manager_factory

    def _ensure_key_vault_client_factory(self) -> Callable[..., AsyncIterator[SecretClient]]:
        if self._key_vault_client_factory is None:
            self._key_vault_client_factory = self._build_key_vault_client_factory()
        return self._key_vault_client_factory

    def _build_secrets_manager_factory(self) -> Callable[..., AsyncIterator[Any]]:
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
            async with aioboto3.client("secretsmanager", **client_kwargs) as client:
                yield client

        return factory

    def _build_key_vault_client_factory(self) -> Callable[..., AsyncIterator[SecretClient]]:
        vault_name = self._settings.azure_key_vault_name
        if not vault_name:
            raise RuntimeError("AZURE_KEY_VAULT_NAME must be configured to mirror secrets.")

        vault_url = f"https://{vault_name}.vault.azure.net"

        @asynccontextmanager
        async def factory() -> AsyncIterator[SecretClient]:
            credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            client = SecretClient(vault_url=vault_url, credential=credential)
            try:
                yield client
            finally:
                await client.close()
                await credential.close()

        return factory

    async def run(
        self,
        sources: Iterable[TherapistSource],
        *,
        dry_run: bool = False,
        prefix: str | None = None,
    ) -> SyncResult:
        result = SyncResult()
        normalized_records: list[NormalizedTherapist] = []

        source_list = list(sources)

        try:
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
        finally:
            self._record_metrics(result, sources=source_list, dry_run=dry_run)

    async def mirror_secrets(
        self,
        mappings: Sequence[SecretMirrorMapping],
        *,
        dry_run: bool = False,
    ) -> list[SecretMirrorResult]:
        if not mappings:
            return []

        results: list[SecretMirrorResult] = []
        secret_payloads: list[tuple[SecretMirrorMapping, str, str | None]] = []
        secrets_factory = self._ensure_secrets_manager_factory()

        async with secrets_factory() as secrets_client:
            for mapping in mappings:
                try:
                    response = await secrets_client.get_secret_value(SecretId=mapping.source_secret_id)
                except Exception as exc:
                    logger.warning(
                        "Failed to read secret %s from AWS Secrets Manager: %s",
                        mapping.source_secret_id,
                        exc,
                        exc_info=exc,
                    )
                    results.append(
                        SecretMirrorResult(
                            source_secret_id=mapping.source_secret_id,
                            target_secret_name=mapping.target_secret_name,
                            status="error",
                            message=f"Fetch failed: {exc}",
                        )
                    )
                    continue

                secret_value = response.get("SecretString")
                if secret_value is None:
                    binary_value = response.get("SecretBinary")
                    if binary_value is None:
                        results.append(
                            SecretMirrorResult(
                                source_secret_id=mapping.source_secret_id,
                                target_secret_name=mapping.target_secret_name,
                                status="error",
                                message="Secret payload missing SecretString and SecretBinary.",
                            )
                        )
                        continue
                    secret_value = base64.b64decode(binary_value).decode("utf-8")

                version_id = response.get("VersionId")
                secret_payloads.append((mapping, secret_value, version_id))

        if dry_run:
            for mapping, _, version_id in secret_payloads:
                results.append(
                    SecretMirrorResult(
                        source_secret_id=mapping.source_secret_id,
                        target_secret_name=mapping.target_secret_name,
                        status="skipped",
                        message="Dry run enabled; Key Vault update skipped.",
                        version_id=version_id,
                    )
                )
            self._record_secret_metrics(results, dry_run=True)
            return results

        key_vault_factory = self._ensure_key_vault_client_factory()
        async with key_vault_factory() as key_vault_client:
            for mapping, secret_value, version_id in secret_payloads:
                try:
                    await key_vault_client.set_secret(mapping.target_secret_name, secret_value)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning(
                        "Failed to write secret %s to Key Vault: %s",
                        mapping.target_secret_name,
                        exc,
                        exc_info=exc,
                    )
                    results.append(
                        SecretMirrorResult(
                            source_secret_id=mapping.source_secret_id,
                            target_secret_name=mapping.target_secret_name,
                            status="error",
                            message=f"Key Vault update failed: {exc}",
                            version_id=version_id,
                        )
                    )
                else:
                    results.append(
                        SecretMirrorResult(
                            source_secret_id=mapping.source_secret_id,
                            target_secret_name=mapping.target_secret_name,
                            status="updated",
                            message="Secret replicated to Key Vault.",
                            version_id=version_id,
                        )
                    )

        self._record_secret_metrics(results, dry_run=False)
        return results

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

    def _record_metrics(
        self,
        result: SyncResult,
        *,
        sources: Sequence[TherapistSource],
        dry_run: bool,
    ) -> None:
        if not self._metrics_path:
            return

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "bucket": self._settings.s3_therapists_bucket,
            "source_count": len(sources),
            "sources": [source.name for source in sources],
            "result": {
                "total_raw": result.total_raw,
                "normalized": result.normalized,
                "written": result.written,
                "skipped": result.skipped,
                "errors": list(result.errors),
            },
        }

        try:
            target = self._metrics_path
            if not target.suffix:
                target = target / "data_sync_metrics.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Failed to persist data sync metrics: %s", exc, exc_info=exc)

    def _record_secret_metrics(
        self,
        results: Sequence[SecretMirrorResult],
        *,
        dry_run: bool,
    ) -> None:
        if not self._metrics_path or not results:
            return

        base_path = self._metrics_path
        if base_path.suffix:
            target = base_path.with_name(f"{base_path.stem}_secrets{base_path.suffix}")
        else:
            target = base_path / "data_sync_secret_metrics.json"

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "result_count": len(results),
            "results": [
                {
                    "source_secret_id": result.source_secret_id,
                    "target_secret_name": result.target_secret_name,
                    "status": result.status,
                    "message": result.message,
                    "version_id": result.version_id,
                }
                for result in results
            ],
        }

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Failed to persist secret mirror metrics: %s", exc, exc_info=exc)


def _build_sources(source_specs: Sequence[str], *, locale: str) -> list[TherapistSource]:
    sources: list[TherapistSource] = []
    for source_spec in source_specs:
        if source_spec.startswith("http"):
            sources.append(HttpJSONSource(url=source_spec, locale=locale))
        else:
            path = pathlib.Path(source_spec).expanduser()
            sources.append(LocalFileSource(path=path, locale=locale, name=path.name))
    return sources


def _parse_secret_mappings(raw_mappings: Sequence[str]) -> list[SecretMirrorMapping]:
    mappings: list[SecretMirrorMapping] = []
    for item in raw_mappings:
        parts = item.split(":", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid --mirror-secret value {item!r}. Expected format SECRET_ID:KEY_VAULT_SECRET_NAME."
            )
        source_id, target_name = (part.strip() for part in parts)
        if not source_id or not target_name:
            raise ValueError(
                f"Invalid --mirror-secret value {item!r}. Both source and target names are required."
            )
        mappings.append(
            SecretMirrorMapping(
                source_secret_id=source_id,
                target_secret_name=target_name,
            )
        )
    return mappings


async def _run(args: argparse.Namespace) -> DataSyncOutcome:
    settings = get_settings()
    agent = DataSyncAgent(settings)
    sources = _build_sources(args.source, locale=args.locale)
    therapist_result: SyncResult | None = None
    if sources:
        therapist_result = await agent.run(
            sources,
            dry_run=args.dry_run,
            prefix=args.prefix,
        )

    secret_mappings = _parse_secret_mappings(args.mirror_secret)
    secret_results: list[SecretMirrorResult] = []
    if secret_mappings:
        secret_results = await agent.mirror_secrets(secret_mappings, dry_run=args.dry_run)

    return DataSyncOutcome(
        therapist_result=therapist_result,
        secret_results=secret_results,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    parser = argparse.ArgumentParser(
        prog="mindwell-data-sync",
        description="Fetch therapist sources and publish normalized profiles to S3.",
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
        "--mirror-secret",
        action="append",
        default=[],
        metavar="SECRET_ID:KEY_VAULT_NAME",
        help=(
            "Mirror a secret from AWS Secrets Manager to Azure Key Vault. "
            "Format: SECRET_ID:KEY_VAULT_SECRET_NAME. May be provided multiple times."
        ),
    )

    args = parser.parse_args()
    if not args.source and not args.mirror_secret:
        parser.error("At least one --source or --mirror-secret must be provided.")

    try:
        result = asyncio.run(_run(args))
    except Exception as exc:  # pragma: no cover - CLI failure path
        logger.exception("Data Sync agent failed: %s", exc)
        raise SystemExit(1) from exc

    if result.therapist_result:
        logger.info(
            "Therapist data sync: %s raw -> %s normalized -> %s written (skipped=%s).",
            result.therapist_result.total_raw,
            result.therapist_result.normalized,
            result.therapist_result.written,
            result.therapist_result.skipped,
        )

    if result.secret_results:
        summary = ", ".join(
            f"{item.target_secret_name}:{item.status}" for item in result.secret_results
        )
        logger.info("Secret mirroring completed: %s", summary)


if __name__ == "__main__":
    main()
