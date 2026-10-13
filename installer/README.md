# DLite Installer

This folder contains everything needed to build a professional, modern Windows
installer for DLite and to set up the browser extension in one click.

## Files

| File | Purpose |
|---|---|
| `DLite.spec` | PyInstaller spec — builds the standalone `DLite.exe` bundle. |
| `DLite-Setup.iss` | Inno Setup script — packages the bundle into a polished installer. |
| `build_installer.bat` | One-click build: installs deps, runs PyInstaller, runs Inno Setup. |
| `install_browser_extensions.py` | One-click helper that registers the native host and opens the right browser page to load the extension. |

## Building the installer

### Prerequisites

- Python 3.10+ (with `pip`)
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (for the `.exe` installer)

### Steps

```bat
:: from the repo root
installer\build_installer.bat
```

This will:

1. Install PyInstaller (if missing).
2. Build `dist\DLite\` with PyInstaller (using `DLite.spec`).
3. Compile `dist\DLite-Setup.exe` with Inno Setup.

The final installer is `dist\DLite-Setup.exe`. Distribute that file — it
contains the whole app, the browser extensions, and the native messaging host.

> If you only want a portable `.exe` (no installer), run:
> `pyinstaller installer\DLite.spec --noconfirm`
> The result is in `dist\DLite\DLite.exe`.

## Installing the browser extension (easy way)

After installing DLite, the Start Menu contains a
**"Setup Browser Extension"** shortcut. Click it — it will:

1. Register the native messaging host for Chrome, Edge, Brave, Opera, and Firefox.
2. Open the right `chrome://extensions` / `about:debugging` page in each
   detected browser.

You then just click **Load unpacked** (or **Load Temporary Add-on** for
Firefox) and pick the bundled `browser-extension/<browser>` folder.

From source you can also run:

```bash
python installer/install_browser_extensions.py                 # all detected browsers
python installer/install_browser_extensions.py --browser chrome
python installer/install_browser_extensions.py --browser firefox
```

## Contact

Maintainer: **Safouane Baadoud** — <safouaneescrow@gmail.com>