"""Start Atlas — Gemini Research Studio."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from atlas.app_data import AppDataPaths
from atlas.logging_utils import setup_logging
from atlas.ui import AtlasWindow, LoadingSplash
from atlas.updater import UpdateManager
from atlas.version import APP_VERSION, UPDATE_MANIFEST_URL


def main() -> int:
    app_data = AppDataPaths(app_name="Atlas")
    logger = setup_logging(log_dir_name=str(app_data.logs_dir.relative_to(app_data.root.parent)))
    logger.info("Starting Atlas application")

    update_manager = UpdateManager(current_version=APP_VERSION, manifest_url=UPDATE_MANIFEST_URL)
    update_result = update_manager.check_for_updates()
    if update_result.available:
        logger.info("Update available: %s -> %s", update_result.current_version, update_result.latest_version)

    app = QApplication(sys.argv)
    app.setApplicationName("Atlas Gemini Research Studio")
    app.setOrganizationName("AtlasResearch")
    app.setStyle("Fusion")

    splash = LoadingSplash()
    splash.show()
    splash.raise_()
    splash.start()
    app.processEvents()

    window = AtlasWindow()
    window.hide()

    def reveal_main_window() -> None:
        splash.close()
        window.show()
        window.raise_()
        window.activateWindow()

    QTimer.singleShot(5000, reveal_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())