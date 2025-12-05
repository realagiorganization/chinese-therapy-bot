from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DemoCodeEntry:
    """Normalized demo-code record loaded from an administrator-managed file."""

    code: str
    label: str | None = None
    chat_token_quota: int | None = None


class DemoCodeRegistry:
    """File-backed registry resolving demo codes to metadata."""

    def __init__(
        self,
        file_path: str | None,
        default_chat_quota: int,
    ) -> None:
        path = Path(file_path).expanduser() if file_path else None
        if not path or not path.exists():
            fallback = Path(__file__).resolve().parents[2] / "config" / "demo_codes.json"
            if fallback.exists():
                logger.info(
                    "Файл демо-кодов не найден по указанному пути; используем встроенный список %s",
                    fallback,
                )
                path = fallback
        self._path = path
        self._default_chat_quota = default_chat_quota if default_chat_quota >= 0 else 0
        self._lock = threading.Lock()
        self._cache: dict[str, DemoCodeEntry] = {}
        self._fallback_cache: dict[str, DemoCodeEntry | None] = {}
        self._mtime: float | None = None
        self._load(force=True)

    def lookup(self, code: str | None) -> DemoCodeEntry | None:
        """Return entry for the provided code if it exists."""
        if not code:
            return None
        key = code.strip()
        if not key:
            return None
        self._load()
        direct = self._cache.get(key)
        if direct:
            return direct

        lowered = key.casefold()
        if lowered in self._fallback_cache:
            return self._fallback_cache[lowered]
        return None

    def _load(self, force: bool = False) -> None:
        if not self._path:
            return
        try:
            stat = self._path.stat()
        except FileNotFoundError:
            if self._cache and force:
                self._cache = {}
                self._fallback_cache = {}
                self._mtime = None
            return

        if not force and self._mtime and stat.st_mtime <= self._mtime:
            return

        with self._lock:
            try:
                with self._path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except json.JSONDecodeError as exc:
                logger.warning("Не удалось разобрать файл демо-кодов %s: %s", self._path, exc)
                return
            except OSError as exc:
                logger.warning("Не удалось прочитать файл демо-кодов %s: %s", self._path, exc)
                return

            entries = {}
            fallback: dict[str, DemoCodeEntry | None] = {}
            raw_codes = payload.get("codes") if isinstance(payload, dict) else None
            if not isinstance(raw_codes, list):
                raw_codes = []

            for raw in raw_codes:
                if not isinstance(raw, dict):
                    continue
                code = str(raw.get("code", "")).strip()
                if not code:
                    continue
                label = str(raw.get("label", "")).strip() or None
                chat_quota = raw.get("chat_token_quota")
                chat_quota_value = (
                    int(chat_quota) if isinstance(chat_quota, int) and chat_quota >= 0 else None
                )
                entry = DemoCodeEntry(
                    code=code,
                    label=label,
                    chat_token_quota=(
                        chat_quota_value
                        if chat_quota_value is not None
                        else self._default_chat_quota
                    ),
                )
                if code in entries:
                    logger.warning(
                        "Демо-код %s указан неоднократно в %s — будет использовано последнее значение.",
                        code,
                        self._path,
                    )
                entries[code] = entry

                lowered = code.casefold()
                if lowered in fallback:
                    fallback[lowered] = None
                else:
                    fallback[lowered] = entry

            self._cache = entries
            self._fallback_cache = fallback
            self._mtime = stat.st_mtime


__all__ = ["DemoCodeRegistry", "DemoCodeEntry"]
