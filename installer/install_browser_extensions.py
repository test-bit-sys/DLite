"""
DLite — Browser extension easy installer.

This helper does two things for the user, in one click:
  1. Registers the native messaging host (so the browser can talk to DLite).
  2. Opens the browser on the right "load unpacked extension" page so the user
     just has to click "Load unpacked" / "Load Temporary Add-on" and pick the
     bundled extension folder.

Usage:
    python installer/install_browser_extensions.py            # detect & register all
    python installer/install_browser_extensions.py --browser chrome
    python installer/install_browser_extensions.py --browser firefox
    python installer/install_browser_extensions.py --browser edge
    python installer/install_browser_extensions.py --browser brave
    python installer/install_browser_extensions.py --browser opera
    python installer/install_browser_extensions.py --browser all

No admin rights required — everything is written under HKCU.
"""

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NATIVE_HOST = ROOT / "native_host"
INSTALL_HOST = NATIVE_HOST / "install_host.py"
EXT_CHROMIUM = ROOT / "browser-extension" / "chromium"
EXT_FIREFOX = ROOT / "browser-extension" / "firefox"

# Browser -> (extension dir, page to open that makes loading easy)
BROWSERS = {
    "chrome": ("Chrome",  EXT_CHROMIUM, "chrome://extensions"),
    "edge":   ("Edge",    EXT_CHROMIUM, "edge://extensions"),
    "brave":  ("Brave",   EXT_CHROMIUM, "brave://extensions"),
    "opera":  ("Opera",   EXT_CHROMIUM, "opera://extensions"),
    "firefox":("Firefox", EXT_FIREFOX, "about:debugging#/runtime/this-firefox"),
}


def register_native_host() -> bool:
    """Run native_host/install_host.py to register manifests in the registry."""
    if not INSTALL_HOST.exists():
        print(f"[!] Native host installer not found: {INSTALL_HOST}")
        return False
    print("\n[1/2] Registering native messaging host...")
    try:
        subprocess.run([sys.executable, str(INSTALL_HOST)], check=True)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[!] Failed to register native host: {exc}")
        return False


def open_extension_page(browser_key: str) -> bool:
    name, ext_dir, url = BROWSERS[browser_key]
    print(f"\n[2/2] Opening {name} to load the extension...")
    print("      Extension folder to select:")
    print(f"        {ext_dir}")
    try:
        webbrowser.open(url)
        print(f"\n  In {name}:")
        if browser_key == "firefox":
            print('   1. Click "Load Temporary Add-on..."')
            print(f"   2. Select: {ext_dir / 'manifest.json'}")
        else:
            print('   1. Enable "Developer mode" (top-right toggle).')
            print('   2. Click "Load unpacked".')
            print(f"   3. Select the folder: {ext_dir}")
        print("\n  Make sure DLite is running, then click a download link to test.")
        return True
    except Exception as exc:
        print(f"[!] Could not open browser: {exc}")
        print(f"    Open this URL manually: {url}")
        return False


def detect_browsers() -> list[str]:
    """Best-effort detection of installed browsers on Windows."""
    import os
    found = []
    candidates = {
        "chrome":  [os.environ.get("PROGRAMFILES"), r"Google\Chrome\Application\chrome.exe"],
        "edge":    [os.environ.get("PROGRAMFILES(x86)"), r"Microsoft\Edge\Application\msedge.exe"],
        "brave":   [os.environ.get("PROGRAMFILES"), r"BraveSoftware\Brave-Browser\Application\brave.exe"],
        "opera":   [os.environ.get("APPDATA"), r"Opera Software\Opera Stable\Opera.exe"],
        "firefox": [os.environ.get("PROGRAMFILES"), r"Mozilla Firefox\firefox.exe"],
    }
    for key, (base, rel) in candidates.items():
        if base and Path(base, rel).exists():
            found.append(key)
    return found


def main():
    if sys.platform != "win32":
        print("This helper only supports Windows.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="DLite browser extension installer")
    parser.add_argument("--browser", choices=list(BROWSERS) + ["all"],
                        default="all", help="Which browser to set up (default: all)")
    args = parser.parse_args()

    print("=" * 48)
    print(" DLite — Browser Extension Installer")
    print("=" * 48)

    # Step 1: register the native messaging host once.
    register_native_host()

    # Step 2: open the right page in the chosen browser(s).
    if args.browser == "all":
        targets = detect_browsers() or ["chrome", "firefox"]
    else:
        targets = [args.browser]

    for b in targets:
        if b not in BROWSERS:
            continue
        open_extension_page(b)

    print("\n" + "=" * 48)
    print(" Done! If DLite is running, downloads will be captured")
    print(" automatically from supported browsers.")
    print(" Contact: safouaneescrow@gmail.com")
    print("=" * 48)


if __name__ == "__main__":
    main()