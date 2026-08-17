from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from atlas.app_data import AppDataPaths
from atlas.updater import UpdateManager


class UpdateManagerTests(unittest.TestCase):
    def test_stage_update_uses_appdata_and_preserves_user_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app_data = AppDataPaths(base_dir=Path(temp_dir) / "AtlasAppData", app_name="Atlas")
            app_root = Path(temp_dir) / "installed-app"
            app_root.mkdir()
            (app_root / "settings.json").write_text('{"keep": true}', encoding="utf-8")
            source = Path(temp_dir) / "update.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("main.py", "print('updated')\n")

            manager = UpdateManager(current_version="1.0.0", manifest_url="https://example.com/manifest.json", app_data=app_data)
            file_url = source.as_uri()
            checksum = hashlib.sha256(source.read_bytes()).hexdigest()
            staged = manager.stage_update(file_url, expected_hash=checksum)
            self.assertTrue(staged.exists())
            self.assertTrue((app_data.pending_dir / "update.json").exists())

            backup = manager.backup_current_app(app_root)
            self.assertTrue(backup.exists())
            self.assertTrue((backup / "settings.json").exists())

    def test_install_update_keeps_user_data_folder_intact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app_data = AppDataPaths(base_dir=Path(temp_dir) / "AtlasAppData", app_name="Atlas")
            app_root = Path(temp_dir) / "installed-app"
            app_root.mkdir()
            (app_root / "main.py").write_text("print('old')\n", encoding="utf-8")
            (app_root / "data").mkdir()
            (app_root / "data" / "storage.json").write_text('{"user": true}', encoding="utf-8")

            staged_dir = app_root.parent / "staged-update"
            staged_dir.mkdir()
            (staged_dir / "main.py").write_text("print('new')\n", encoding="utf-8")
            (staged_dir / "readme.txt").write_text("updated", encoding="utf-8")

            manager = UpdateManager(current_version="1.0.0", manifest_url="https://example.com/manifest.json", app_data=app_data)
            result = manager.install_update(app_root, staged_dir)
            self.assertTrue(result.exists())
            self.assertEqual((app_root / "main.py").read_text(encoding="utf-8"), "print('new')\n")
            self.assertTrue((app_root / "data" / "storage.json").exists())


if __name__ == "__main__":
    unittest.main()
