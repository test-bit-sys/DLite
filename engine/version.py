"""Single source of truth for application version and author metadata.

Every place that needs the version (splash screen, QApplication metadata,
packaging, CI) should import from here instead of hardcoding it.
"""

APP_NAME = "DLite"
APP_VERSION = "1.1.0"
APP_AUTHOR = "Safouane Baadoud"
APP_AUTHOR_EMAIL = "safouaneescrow@gmail.com"
APP_URL = "https://github.com/test-bit-sys/DLite"

__version__ = APP_VERSION
