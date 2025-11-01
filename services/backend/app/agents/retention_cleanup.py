from __future__ import annotations

import argparse
import asyncio
import logging
from calendar import monthrange
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import aioboto3

from app.core.config import AppSettings, get_settings


logger = logging.getLogger("mindwell.retention")


@dataclass(slots=True)
class CleanupResult:
    """Statistics describing a single retention cleanup pass."""

    bucket: str
    prefix: str
    scanned: int = 0
    archive_candidates: int = 0
    delete_candidates: int = 0
    deleted: int = 0
    deleted_keys: list[str] = field(default_factory=list)
    dry_run: bool = True


class RetentionCleanupAgent:
    """Enforce MindWell data retention policies for S3 objects."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        s3_client_factory: Callable[[], AsyncIterator[Any]] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ):
        if not settings.s3_conversation_logs_bucket and not settings.s3_summaries_bucket:
            raise RuntimeError(
                "Retention cleanup requires at least one S3 bucket to be configured."
            )
        self._settings = settings
        self._s3_client_factory = s3_client_factory or self._build_s3_client_factory()
        self._now_factory = now_factory or (lambda: datetime.now(timezone.utc))

    async def run(
        self,
        *,
        dry_run: bool = True,
        include: Iterable[str] | None = None,
        batch_size: int = 500,
    ) -> dict[str, CleanupResult]:
        """Execute retention cleanup for selected data domains."""
        selections = set(include or {"conversations", "summaries"})
        if "all" in selections:
            selections = {"conversations", "summaries"}

        results: dict[str, CleanupResult] = {}

        if "conversations" in selections and self._settings.s3_conversation_logs_bucket:
            results["conversations"] = await self._cleanup_conversation_logs(
                dry_run=dry_run, batch_size=batch_size
            )

        if "summaries" in selections and self._settings.s3_summaries_bucket:
            results["daily_summaries"] = await self._cleanup_daily_summaries(
                dry_run=dry_run, batch_size=batch_size
            )

        return results

    async def _cleanup_conversation_logs(
        self, *, dry_run: bool, batch_size: int
    ) -> CleanupResult:
        bucket = self._settings.s3_conversation_logs_bucket
        prefix = (self._settings.s3_conversation_logs_prefix or "conversations/").rstrip("/") + "/"
        result = CleanupResult(bucket=bucket or "", prefix=prefix, dry_run=dry_run)

        retention_months = max(0, self._settings.conversation_logs_retention_months)
        delete_months = max(retention_months, self._settings.conversation_logs_delete_months)
        now = self._now()
        archive_threshold = subtract_months(now, retention_months)
        delete_threshold = subtract_months(now, delete_months)

        delete_keys: list[str] = []

        async with self._s3_client_factory() as client:
            async for obj in self._iterate_objects(client, bucket, prefix):
                result.scanned += 1
                last_modified = self._coerce_datetime(obj.get("LastModified"))
                key = obj.get("Key")
                if not last_modified or not key:
                    logger.debug("Skipping object without metadata: %s", obj)
                    continue

                if last_modified <= archive_threshold:
                    result.archive_candidates += 1
                if last_modified <= delete_threshold:
                    delete_keys.append(key)

            if dry_run:
                result.delete_candidates = len(delete_keys)
                result.deleted_keys = delete_keys
                logger.info(
                    "[DRY-RUN] Conversation log cleanup: %s candidates for deletion in s3://%s/%s",
                    result.delete_candidates,
                    bucket,
                    prefix,
                )
                return result

            if delete_keys:
                deleted = await self._delete_in_batches(client, bucket, delete_keys, batch_size)
                result.deleted = deleted
            result.delete_candidates = len(delete_keys)
            result.deleted_keys = delete_keys
            logger.info(
                "Conversation log cleanup: deleted %s objects (candidates=%s) in s3://%s/%s",
                result.deleted,
                result.delete_candidates,
                bucket,
                prefix,
            )
            return result

    async def _cleanup_daily_summaries(
        self, *, dry_run: bool, batch_size: int
    ) -> CleanupResult:
        bucket = self._settings.s3_summaries_bucket
        prefix = "daily/"
        result = CleanupResult(bucket=bucket or "", prefix=prefix, dry_run=dry_run)

        retention_months = max(0, self._settings.daily_summary_retention_months)
        now = self._now()
        delete_threshold = subtract_months(now, retention_months)

        delete_keys: list[str] = []

        async with self._s3_client_factory() as client:
            async for obj in self._iterate_objects(client, bucket, prefix):
                result.scanned += 1
                last_modified = self._coerce_datetime(obj.get("LastModified"))
                key = obj.get("Key")
                if not last_modified or not key:
                    logger.debug("Skipping summary object without metadata: %s", obj)
                    continue

                if last_modified <= delete_threshold:
                    delete_keys.append(key)

            if dry_run:
                result.delete_candidates = len(delete_keys)
                result.deleted_keys = delete_keys
                logger.info(
                    "[DRY-RUN] Daily summary cleanup: %s candidates for deletion in s3://%s/%s",
                    result.delete_candidates,
                    bucket,
                    prefix,
                )
                return result

            if delete_keys:
                deleted = await self._delete_in_batches(client, bucket, delete_keys, batch_size)
                result.deleted = deleted
            result.delete_candidates = len(delete_keys)
            result.deleted_keys = delete_keys
            logger.info(
                "Daily summary cleanup: deleted %s objects (candidates=%s) in s3://%s/%s",
                result.deleted,
                result.delete_candidates,
                bucket,
                prefix,
            )
            return result

    def _build_s3_client_factory(self) -> Callable[[], AsyncIterator[Any]]:
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

    async def _iterate_objects(
        self, client: Any, bucket: str | None, prefix: str
    ) -> AsyncIterator[dict[str, Any]]:
        if not bucket:
            return
        continuation_token: str | None = None

        while True:
            kwargs = {"Bucket": bucket, "Prefix": prefix}
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token

            response = await client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []) or []:
                yield obj

            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")

    async def _delete_in_batches(
        self,
        client: Any,
        bucket: str | None,
        keys: list[str],
        batch_size: int,
    ) -> int:
        if not bucket or not keys:
            return 0

        total_deleted = 0
        for start in range(0, len(keys), batch_size):
            chunk = keys[start : start + batch_size]
            response = await client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": key} for key in chunk], "Quiet": True},
            )
            deleted = response.get("Deleted")
            if isinstance(deleted, list):
                total_deleted += len(deleted)
            else:
                total_deleted += len(chunk)
        return total_deleted

    def _coerce_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return None

    def _now(self) -> datetime:
        now = self._now_factory()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc)


def subtract_months(dt: datetime, months: int) -> datetime:
    """Return datetime shifted backwards by the provided month count."""
    if months <= 0:
        return dt
    year = dt.year
    month = dt.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(dt.day, monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enforce MindWell transcript and summary retention policies."
    )
    parser.add_argument(
        "--include",
        nargs="+",
        choices=("conversations", "summaries", "all"),
        default=["all"],
        help="Data domains to process (default: all).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of objects to delete per S3 batch request.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute deletions (omit for dry-run).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity.",
    )
    return parser.parse_args()


async def _async_main(args: argparse.Namespace) -> dict[str, CleanupResult]:
    logging.basicConfig(level=getattr(logging, args.log_level))
    settings = get_settings()
    agent = RetentionCleanupAgent(settings)
    include = args.include or ["all"]
    results = await agent.run(
        dry_run=not args.execute,
        include=include,
        batch_size=args.batch_size,
    )

    for domain, result in results.items():
        logger.info(
            "Cleanup completed for %s: scanned=%s delete_candidates=%s deleted=%s dry_run=%s",
            domain,
            result.scanned,
            result.delete_candidates,
            result.deleted,
            result.dry_run,
        )
    return results


def main() -> None:
    args = parse_args()
    asyncio.run(_async_main(args))


if __name__ == "__main__":
    main()
