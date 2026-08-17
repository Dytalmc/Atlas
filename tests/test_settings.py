from pathlib import Path

from PyQt6.QtCore import QSettings

from atlas.settings import SettingsStore


def test_task_model_settings_round_trip(tmp_path: Path) -> None:
    store = SettingsStore()
    store._settings = QSettings("AtlasTaskModelTest", "AtlasTest")
    store._settings.clear()

    store.save(
        api_key="demo-key",
        model="gemini-3.6-flash",
        downloads_dir=tmp_path,
        task_models={
            "chat": "gemini-3-flash-preview",
            "build": "gemini-3.5-flash",
        },
    )

    loaded = store.load()

    assert loaded.model == "gemini-3.6-flash"
    assert loaded.task_models["chat"] == "gemini-3-flash-preview"
    assert loaded.task_models["build"] == "gemini-3.5-flash"
    assert loaded.task_models["research"] == "gemini-3.6-flash"
