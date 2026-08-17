"""Small, explicit local settings wrapper."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QSettings

from .app_data import AppDataPaths


DEFAULT_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
)

DEFAULT_TASK_MODELS = {
    "default": DEFAULT_MODELS[0],
    "chat": DEFAULT_MODELS[0],
    "research": DEFAULT_MODELS[0],
    "analysis": DEFAULT_MODELS[0],
    "build": DEFAULT_MODELS[0],
    "repair": DEFAULT_MODELS[0],
}


@dataclass(frozen=True)
class AppSettings:
    api_key: str
    model: str
    task_models: dict[str, str]
    downloads_dir: Path


class SettingsStore:
    """Persists only user preferences on the current computer."""

    def __init__(self) -> None:
        self._app_data = AppDataPaths(app_name="Atlas")
        self._settings_path = self._app_data.settings_file("settings.json")
        self._settings = QSettings("AtlasResearch", "Atlas Gemini Research Studio")
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def default_downloads_dir() -> Path:
        downloads = Path.home() / "Downloads"
        return downloads if downloads.exists() else Path.home()

    @staticmethod
    def _normalize_model(value: str | None, fallback: str) -> str:
        candidate = str(value or "").strip()
        return candidate or fallback

    def _task_model_map(self, fallback_model: str) -> dict[str, str]:
        raw = self._settings.value("task_models")
        parsed: dict[str, str] = {}

        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {}
        elif isinstance(raw, dict):
            parsed = dict(raw)

        task_models: dict[str, str] = {}
        for name, fallback in DEFAULT_TASK_MODELS.items():
            task_models[name] = self._normalize_model(parsed.get(name), fallback_model if name == "default" else fallback)
        task_models["default"] = self._normalize_model(task_models.get("default"), fallback_model)
        return task_models

    def load(self) -> AppSettings:
        saved_key = str(self._settings.value("api_key", ""))
        api_key = os.environ.get("GEMINI_API_KEY", saved_key).strip()
        model = self._normalize_model(str(self._settings.value("model", DEFAULT_MODELS[0])), DEFAULT_MODELS[0])
        raw_directory = str(self._settings.value("downloads_dir", str(self.default_downloads_dir())))
        directory = Path(raw_directory).expanduser()
        task_models = self._task_model_map(model)
        return AppSettings(api_key=api_key, model=model, task_models=task_models, downloads_dir=directory)

    def save(
        self,
        *,
        api_key: str,
        model: str,
        downloads_dir: Path,
        task_models: dict[str, str] | None = None,
    ) -> None:
        normalized_model = self._normalize_model(model, DEFAULT_MODELS[0])
        normalized_tasks = {}
        for name, fallback in DEFAULT_TASK_MODELS.items():
            selected = (task_models or {}).get(name, fallback)
            normalized_tasks[name] = self._normalize_model(selected, normalized_model if name == "default" else fallback)
        normalized_tasks["default"] = self._normalize_model(normalized_tasks.get("default"), normalized_model)

        self._settings.setValue("api_key", api_key.strip())
        self._settings.setValue("model", normalized_model)
        self._settings.setValue("downloads_dir", str(downloads_dir))
        self._settings.setValue("task_models", json.dumps(normalized_tasks))
        self._settings.sync()

        payload = {
            "api_key": api_key.strip(),
            "model": normalized_model,
            "downloads_dir": str(downloads_dir),
            "task_models": normalized_tasks,
        }
        self._settings_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

