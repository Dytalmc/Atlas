from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from atlas.app_data import AppDataPaths
from atlas.updater import UpdateManager


class AppDataTests(unittest.TestCase):
    def test_app_data_paths_are_under_user_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = AppDataPaths(base_dir=Path(temp_dir), app_name="AtlasTest")
            self.assertTrue(paths.root.is_dir())
            self.assertTrue((paths.root / "logs").is_dir())
            self.assertTrue((paths.root / "settings").is_dir())
            self.assertTrue((paths.root / "data").is_dir())
            self.assertTrue((paths.root / "updates").is_dir())

    def test_update_manager_detects_newer_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            version_file = Path(temp_dir) / "manifest.json"
            version_file.write_text(
                json.dumps({"version": "1.2.0", "download_url": "https://example.com/app.zip", "checksum": "abc"}),
                encoding="utf-8",
            )
            manager = UpdateManager(current_version="1.1.0", manifest_url=str(version_file))
            result = manager.check_for_updates()
            self.assertTrue(result.available)
            self.assertEqual(result.latest_version, "1.2.0")
            self.assertFalse(result.requires_restart)


if __name__ == "__main__":
    unittest.main()
