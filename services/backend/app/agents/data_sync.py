from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import pathlib
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence

import aioboto3
import httpx

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


class DataSyncAgent:
    """Normalize therapist profiles and publish them to the configured S3 bucket."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        s3_client_factory: Callable[..., AsyncIterator[Any]] | None = None,
    ):
        if not settings.s3_therapists_bucket:
            raise RuntimeError("S3_BUCKET_THERAPISTS must be configured to run the Data Sync agent.")

        self._settings = settings
        self._s3_client_factory = s3_client_factory or self._build_s3_client_factory()
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


async def _run(args: argparse.Namespace) -> SyncResult:
    settings = get_settings()
    agent = DataSyncAgent(settings)
    sources = _build_sources(args)
    return await agent.run(
        sources,
        dry_run=args.dry_run,
        prefix=args.prefix,
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

    args = parser.parse_args()
    try:
        result = asyncio.run(_run(args))
    except Exception as exc:  # pragma: no cover - CLI failure path
        logger.exception("Data Sync agent failed: %s", exc)
        raise SystemExit(1) from exc

    logger.info(
        "Data Sync completed: %s raw -> %s normalized -> %s written (skipped=%s).",
        result.total_raw,
        result.normalized,
        result.written,
        result.skipped,
    )


if __name__ == "__main__":
    main()
