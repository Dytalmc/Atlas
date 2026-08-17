"""Local, inspectable activity memory for Atlas.

This is intentionally separate from Gemini's optional server-side interaction
storage. Atlas sends each API request with `store=False`; this file is the
user-controlled local record used to give the Chat page context.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QStandardPaths

from .app_data import AppDataPaths

MAX_CONTEXT_CHARS = 500_000
_SENSITIVE_KEY_FRAGMENTS = ("api_key", "apikey", "password", "secret", "token", "authorization", "credential")


class MemoryStore:
    """Append-only JSONL app memory stored in the current user's app-data folder."""

    def __init__(self) -> None:
        self._app_data = AppDataPaths(app_name="Atlas")
        self._directory = self._app_data.data_dir
        self._path = self._app_data.memory_file()
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    @staticmethod
    def _safe_value(value: Any, key: str = "") -> Any:
        """Keep local memory useful without recording credentials or raw bytes."""
        key_lower = key.lower()
        if any(fragment in key_lower for fragment in _SENSITIVE_KEY_FRAGMENTS):
            return "[redacted]"
        if isinstance(value, bytes):
            return f"[raw bytes omitted: {len(value)} bytes]"
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return {str(item_key): MemoryStore._safe_value(item_value, str(item_key)) for item_key, item_value in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [MemoryStore._safe_value(item, key) for item in value]
        if value is None or isinstance(value, (int, float, bool)):
            return value
        return str(value)

    def record(self, event: str, details: dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": self._safe_value(details),
        }
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._directory.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")

    def _records(self) -> list[dict[str, Any]]:
        if not self._path.is_file():
            return []
        records: list[dict[str, Any]] = []
        with self._lock:
            try:
                with self._path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        try:
                            item = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(item, dict):
                            records.append(item)
            except OSError:
                return []
        return records

    def recent_context(self, *, maximum_characters: int = MAX_CONTEXT_CHARS) -> str:
        """Return the newest activity records that fit in a predictable chat context budget."""
        chunks: list[str] = []
        used = 0
        for record in reversed(self._records()):
            if record.get("event") in {"chat_user", "chat_assistant"}:
                continue
            rendered = json.dumps(record, ensure_ascii=False, indent=2)
            if used + len(rendered) + 2 > maximum_characters:
                break
            chunks.append(rendered)
            used += len(rendered) + 2
        if not chunks:
            return "No earlier Atlas activity has been recorded yet."
        chunks.reverse()
        prefix = "LOCAL ATLAS ACTIVITY MEMORY (oldest records may be omitted only if the file exceeds this request budget):\n"
        return prefix + "\n\n".join(chunks)

    def recent_chat(self, *, limit: int = 40) -> list[tuple[str, str]]:
        messages: list[tuple[str, str]] = []
        for record in self._records():
            event = record.get("event")
            details = record.get("details")
            if event not in {"chat_user", "chat_assistant"} or not isinstance(details, dict):
                continue
            message = details.get("message")
            if isinstance(message, str) and message.strip():
                messages.append(("user" if event == "chat_user" else "assistant", message))
        return messages[-limit:]

    def clear(self) -> None:
        """Clear the local activity file; callers should obtain user confirmation first."""
        with self._lock:
            if self._path.exists():
                self._path.unlink()
