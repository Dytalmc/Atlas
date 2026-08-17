"""Update management and background checking for Atlas."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from PyQt6.QtCore import QThread, pyqtSignal

from .logging_utils import setup_logging

# Safely import or fallback version constants to prevent ImportErrors
try:
    from .version import APP_VERSION, UPDATE_MANIFEST_URL
except ImportError:
    try:
        from .version import __version__ as APP_VERSION
        from .version import UPDATE_CHECK_URL as UPDATE_MANIFEST_URL
    except ImportError:
        APP_VERSION = "1.0.0"
        UPDATE_MANIFEST_URL = "https://api.github.com/repos/your-username/atlas-app/releases/latest"

logger = setup_logging()

__version__ = APP_VERSION
UPDATE_CHECK_URL = UPDATE_MANIFEST_URL


@dataclass
class UpdateResult:
    available: bool
    current_version: str
    latest_version: str
    release_url: str = ""


class UpdateManager:
    """Synchronous update manager used during application bootstrap."""

    def __init__(self, current_version: str = APP_VERSION, manifest_url: str = UPDATE_MANIFEST_URL) -> None:
        self.current_version = current_version
        self.manifest_url = manifest_url

    def check_for_updates(self) -> UpdateResult:
        try:
            req = urllib.request.Request(
                self.manifest_url,
                headers={"User-Agent": f"Atlas-App/{self.current_version}"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    latest_tag = data.get("tag_name", "").lstrip("v")
                    html_url = data.get("html_url", "")

                    if latest_tag and self._is_newer(latest_tag, self.current_version):
                        return UpdateResult(
                            available=True,
                            current_version=self.current_version,
                            latest_version=latest_tag,
                            release_url=html_url,
                        )
        except Exception as e:
            logger.debug(f"Update check failed: {e}")

        return UpdateResult(
            available=False,
            current_version=self.current_version,
            latest_version=self.current_version,
        )

    @staticmethod
    def _is_newer(remote: str, local: str) -> bool:
        try:
            r_parts = [int(p) for p in remote.split(".")]
            l_parts = [int(p) for p in local.split(".")]
            return r_parts > l_parts
        except Exception:
            return remote != local


class UpdateCheckerWorker(QThread):
    """Background worker thread to check for application updates on launch."""

    update_checked = pyqtSignal(bool, str, str)  # (has_update, latest_version, release_url)

    def run(self) -> None:
        try:
            req = urllib.request.Request(
                UPDATE_CHECK_URL,
                headers={"User-Agent": f"Atlas-App/{__version__}"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    latest_tag = data.get("tag_name", "").lstrip("v")
                    html_url = data.get("html_url", "")

                    if latest_tag and self._is_newer(latest_tag, __version__):
                        logger.info(f"New update found: v{latest_tag}")
                        self.update_checked.emit(True, latest_tag, html_url)
                        return
        except Exception as e:
            logger.debug(f"Update check skipped or failed: {e}")

        self.update_checked.emit(False, "", "")

    @staticmethod
    def _is_newer(remote: str, local: str) -> bool:
        try:
            r_parts = [int(p) for p in remote.split(".")]
            l_parts = [int(p) for p in local.split(".")]
            return r_parts > l_parts
        except Exception:
            return remote != local