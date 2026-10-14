# Changelog

All notable changes to DLite will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] — 2026-10-14

### Added
- **Download Scheduler** (`engine/scheduler.py` & `gui/scheduler_dialog.py`) — automated scheduling engine capable of starting and pausing queues at set times, with an intuitive scheduling dialog and live status bar indicators.
- **Time-based Bandwidth Throttling Windows** — schedule specific hours (e.g. during daytime/work hours) to enforce bandwidth caps, automatically restoring full speed outside the window (supports overnight intervals).
- **Clipboard URL Monitoring & Auto-Capture** (`engine/clipboard.py`) — automatically detects downloadable URLs copied to the clipboard and prompts for instant queuing without manual copy-pasting. Toggleable in settings, menu, and system tray.
- **Batch URL Pattern Generator** (`engine/pattern_generator.py` & `gui/batch_pattern_dialog.py`) — allows adding batches of downloads via URL templates with range wildcards like `[01-20]`, `[1-50:2]`, and `[a-z]` with live count preview and one-click bulk queuing.
- **Desktop System Tray Completion Notifications** — alerts users with file name and size when transfers finish in the background.
- **Multi-language (i18n) expansions** — full Arabic (العربية) and English translations for scheduler, batch pattern downloading, clipboard monitor, and notifications.
- **Unit test suite expansion** (`tests/test_scheduler_and_tools.py`) — tests covering scheduling time windows, throttling state machine, clipboard heuristics, and pattern expansion logic.

---

## [1.0.1] — 2026-09-23

### Fixed
- **Native host port mismatch** — the native messaging host now reads `native_host_port` from the app settings (`%APPDATA%/DLite/settings.json`) instead of hardcoding `38271`. Previously, changing the TCP port in Settings silently broke all browser integration.
- **Settings dialog** — the TCP port spinner now loads the configured port on open and accepts ports from 1024, consistent with the main window's connection panel.
- **EventBus diagnostics** — a crashing event listener is now logged with a full traceback instead of being silently swallowed, making GUI/engine integration bugs diagnosable from the log file.

### Security
- **Upgraded `requests` to ≥ 2.32.3** — fixes CVE-2024-35195 (SSL certificate verification bypass in `requests.Session`), which directly affects the download engine.

### Changed
- **Centralised versioning** — the app version now lives in `engine/version.py`; the splash screen, `QApplication` metadata, and packaging all read the same constant.
- **Project identity: "DLite"** — a distinctive, original, modern brand identity (Download + Lite) for high-performance downloading.
- **All GitHub links** (README, CONTRIBUTING, browser extensions, website, installer) now point to the official repository at `test-bit-sys/DLite`.

### Added
- **CI pipeline** (GitHub Actions) — automated Ruff linting plus the full pytest suite on every push and pull request, on both Linux and Windows.
- **Release pipeline** — pushing a `v*` tag now builds a portable Windows bundle with PyInstaller and attaches it to a GitHub Release automatically.
- **`pyproject.toml`** — project metadata plus Ruff and pytest configuration.
- **Community health files** — `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.editorconfig`, Dependabot configuration, and `requirements-dev.txt`.

### Removed
- **Marketing website** (`website/`) removed from the repository — it is not part of the published project. The download engine, GUI, extensions, and installer are unaffected.

---

## [1.0.0] — 2026-07-09

### Added
- **One-click Windows installer** — Inno Setup-based installer (`DLite-Setup.exe`) bundling the app, browser extensions, and native host. No admin rights and no Python required.
- **One-click browser extension installer** (`installer/install_browser_extensions.py`) — registers the native host and opens the correct browser page to load the extension in a single click.
- **PyInstaller build pipeline** — `installer/DLite.spec` + `installer/build_installer.bat` produce both a portable `DLite.exe` and the installer.
- **Real-time speed graph** — live 60-second rolling chart of aggregate download throughput.
- **Segment progress visualiser** — per-connection download progress overlay showing which byte ranges are completed.
- **Browser integration** — Chrome, Firefox, Edge, Brave, and Opera extension support via native messaging host.
- **Pre-download confirmation dialog** — intercept downloads from browser, review filename, save location, category, segments, and speed limit before starting.
- **Category sidebar** — auto-categorises downloads into Video, Audio, Documents, Archives, Images, and Programs based on file extension.
- **System tray** — minimise to tray with pause/resume/quit controls; double-click to restore.
- **Context menu** — right-click downloads for pause, resume, cancel, open folder, open file, remove, and delete-with-file actions.
- **Bulk operations** — pause all, resume all, clear completed via menu bar and keyboard shortcuts.
- **Import from text file** — batch-add URLs from a .txt file (one per line, `#` for comments).
- **Search/filter** — live filtering of the download table by filename.
- **Custom User-Agent** — configure the HTTP User-Agent header sent with download requests.
- **Configurable retry** — adjustable retry count and delay for failed downloads.
- **Global speed limit** — cap total download throughput in KB/s.
- **Configurable chunk size** — 128 KB to 1 MB buffer size for tuning memory vs throughput.
- **Download deduplication** — queued/downloading URLs are not duplicated; existing task is returned.
- **Duplicate filename handling** — automatically appends ` (1)`, ` (2)`, etc. when destination file already exists.
- **Auto-promotion** — queued tasks automatically start when an active download slot frees up.
- **Dark & Light themes** — switchable from Settings; dark theme is optimised for long download sessions.
- **Persistent configuration** — JSON config file stored in `%APPDATA%/DLite/config.json`.
- **Rotating log file** — structured logging to `%APPDATA%/DLite/dlite.log` with automatic rotation at 2 MB.
- **In-app log viewer** — real-time system log tab capped at 500 lines to prevent memory bloat.
- **Status bar** — live download count, total aggregate speed, and active download count.
- **Keyboard shortcuts** — comprehensive accelerators for all major actions.

### Website
- Next.js 14 landing page with App Router.
- Premium visual design: animated grid background, noise texture overlay, glow blobs, glass-morphism panels.
- Responsive layout (320px → 4K).
- Dark mode as default with light mode toggle.
- Scroll-triggered reveal animations, magnetic button hover effects, animated counters, speed graph visualisation.
- SEO: Open Graph, Twitter Cards, robots.txt directives, semantic HTML.
- Preconnect to GitHub CDN for faster external link loads.
- Custom gradient text, premium card styles, animated border glow utility.

---

## Types of changes
- **Added** — for new features.
- **Changed** — for changes in existing functionality.
- **Deprecated** — for soon-to-be removed features.
- **Removed** — for now removed features.
- **Fixed** — for any bug fixes.
- **Security** — in case of vulnerabilities.