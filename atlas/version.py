"""Version and update configuration for Atlas."""

from __future__ import annotations

__version__ = "1.0.0"
APP_VERSION = __version__

UPDATE_CHECK_URL = "https://api.github.com/repos/your-username/atlas-app/releases/latest"
UPDATE_MANIFEST_URL = UPDATE_CHECK_URL