"""
Registers the DLite native messaging host with the browsers that support it.
Run this once after installing the desktop app. Windows only - registers the
host manifest path under HKCU so no admin rights are required.
"""

import json
import sys
import winreg
from pathlib import Path

HOST_NAME = "com.dlite.host"

# Use the stable generated Chromium extension ID
CHROMIUM_EXTENSION_IDS = [
    "mkkjhabahmcbbnhkpkahleljolldhdgf",
]

FIREFOX_EXTENSION_ID = "dlite@safouane02"

CHROMIUM_REGISTRY_PATHS = [
    r"Software\Google\Chrome\NativeMessagingHosts",
    r"Software\Microsoft\Edge\NativeMessagingHosts",
    r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
    r"Software\Opera Software\NativeMessagingHosts",
]

FIREFOX_REGISTRY_PATH = r"Software\Mozilla\NativeMessagingHosts"


def build_manifest(host_dir: Path, browser: str) -> dict:
    bat_path = host_dir / "host.bat"

    manifest = {
        "name": HOST_NAME,
        "description": "DLite native messaging host",
        "type": "stdio",
        "path": str(bat_path),
    }

    if browser == "firefox":
        manifest["allowed_extensions"] = [FIREFOX_EXTENSION_ID]
    else:
        manifest["allowed_origins"] = [f"chrome-extension://{ext_id}/" for ext_id in CHROMIUM_EXTENSION_IDS]

    return manifest


def write_manifest_file(host_dir: Path, browser: str) -> Path:
    manifest = build_manifest(host_dir, browser)
    manifest_path = host_dir / f"{HOST_NAME}.{browser}.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest_path


def register_registry_key(registry_path: str, manifest_path: Path):
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{registry_path}\\{HOST_NAME}")
    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest_path))
    winreg.CloseKey(key)


def main():
    host_dir = Path(__file__).parent.resolve()
    python_exe = sys.executable

    # Dynamically create the host.bat launcher using current Python executable
    bat_path = host_dir / "host.bat"
    bat_content = f'@echo off\n"{python_exe}" -u "%~dp0host.py" %*\n'
    try:
        bat_path.write_text(bat_content, encoding="utf-8")
        print(f"Created launcher script: {bat_path}")
    except OSError as exc:
        print(f"Could not create launcher script: {exc}")
        sys.exit(1)

    for registry_path in CHROMIUM_REGISTRY_PATHS:
        manifest_path = write_manifest_file(host_dir, "chromium")
        register_registry_key(registry_path, manifest_path)
        print(f"Registered chromium host in: {registry_path}")

    manifest_path = write_manifest_file(host_dir, "firefox")
    register_registry_key(FIREFOX_REGISTRY_PATH, manifest_path)
    print(f"Registered firefox host in: {FIREFOX_REGISTRY_PATH}")

    print("\nNative messaging host successfully registered!")


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This installer only supports Windows")
        sys.exit(1)
    main()
