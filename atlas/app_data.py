from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppDataPaths:
    """Centralized, update-safe user-data location for Atlas."""

    base_dir: Path | None = None
    app_name: str = "Atlas"

    def __post_init__(self) -> None:
        if self.base_dir is None:
            import os

            base_path = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            object.__setattr__(self, "base_dir", base_path / self.app_name)
        else:
            object.__setattr__(self, "base_dir", Path(self.base_dir).expanduser().resolve())

        self.root.mkdir(parents=True, exist_ok=True)
        for child in ("logs", "settings", "data", "updates", "pending", "staged", "backups", "cache"):
            (self.root / child).mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self.base_dir

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def settings_dir(self) -> Path:
        return self.root / "settings"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def updates_dir(self) -> Path:
        return self.root / "updates"

    @property
    def pending_dir(self) -> Path:
        return self.root / "pending"

    @property
    def staged_dir(self) -> Path:
        return self.root / "staged"

    @property
    def backups_dir(self) -> Path:
        return self.root / "backups"

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    def settings_file(self, name: str = "settings.json") -> Path:
        return self.settings_dir / name

    def memory_file(self, name: str = "atlas-memory.jsonl") -> Path:
        return self.data_dir / name

    def log_file(self, name: str = "atlas.log") -> Path:
        return self.logs_dir / name

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
