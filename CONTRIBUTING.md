# Contributing to DLite

Thank you for your interest in contributing to DLite! 

> **🌟 DLite is an open, community-driven project.** We actively welcome developers of all skill levels, UI designers, testers, and translators from all over the world to help shape the future of this download manager. Whether you want to fix a typo, add a new protocol, or co-maintain a platform port, we'd love to have you onboard!

## Code of Conduct

Please be respectful, constructive, and inclusive. Harassment, offensive language, and unprofessional behavior will not be tolerated.

---

## How to Contribute

### Reporting Bugs

1. Search [existing issues](https://github.com/test-bit-sys/DLite/issues) to avoid duplicates.
2. If no existing issue matches, open a **Bug Report** using the issue template.
3. Include:
   - Steps to reproduce
   - Expected vs actual behavior
   - Your OS (Windows 10/11) and Python version
   - Screenshots if applicable
   - Any relevant log output from `%APPDATA%/DLite/dlite.log`

### Suggesting Features

1. Open a **Feature Request** using the issue template.
2. Describe the feature, the problem it solves, and how it fits into DLite's lightweight philosophy.
3. Be open to discussion — features that add significant complexity or bloat may be declined.

### Pull Requests

1. **Fork** the repository.
2. **Create a branch** from `main` with a descriptive name (`fix/resume-bug`, `feat/scheduler`, etc.).
3. **Make your changes** — keep commits small, focused, and well-described.
4. **Test your changes** — run the existing test suite and add new tests where appropriate.
5. **Ensure the project builds** — `python main.py` must launch without import errors.
6. **Open a Pull Request** against the `main` branch.
7. A maintainer will review your PR. Be responsive to feedback.

---

## Development Setup

### Desktop App

```bash
# Clone the repository
git clone https://github.com/test-bit-sys/DLite.git
cd DLite

# Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

**Prerequisites:**
- Python 3.10+
- PyQt6
- requests
- Windows 10/11 (native messaging host requires Windows registry access)

### Website

```bash
cd website
npm install
npm run dev
```

The website runs on `http://localhost:3000`.

**Prerequisites:**
- Node.js 18+
- npm 9+

### Browser Extension

Load unpacked:
- **Chrome/Edge/Brave/Opera:** Navigate to `chrome://extensions`, enable Developer mode, click "Load unpacked", select `browser-extension/chromium/`.
- **Firefox:** Navigate to `about:debugging#/runtime/this-firefox`, click "Load Temporary Add-on", select `browser-extension/firefox/manifest.json`.

---

## Project Structure

```
dlite/
├── main.py                 -- Application entry point
├── engine/                 -- Download engine (core logic)
│   ├── config.py           -- Persistent configuration (JSON file)
│   ├── downloader.py       -- Multi-segment HTTP downloader with resume
│   ├── events.py           -- Internal pub/sub event bus
│   ├── logger.py           -- Structured logging with rotation
│   ├── models.py           -- DownloadTask and DownloadStatus data classes
│   └── queue_manager.py    -- Task lifecycle, concurrency gating, deduplication
├── gui/                    -- PyQt6 desktop UI
│   ├── main_window.py      -- Main application window (table, toolbar, menus)
│   ├── add_download_dialog.py -- URL add and confirmation dialog
│   ├── settings_dialog.py  -- Tabbed settings dialog
│   └── theme.py            -- Dark / light theme stylesheets
├── browser-extension/      -- Browser companion extensions
│   ├── chromium/           -- Chrome/Edge/Brave/Opera (Manifest V3)
│   └── firefox/            -- Firefox (WebExtensions API)
├── native_host/            -- Native messaging host for browser integration
│   ├── host.py             -- STDIO bridge between extension and desktop app
│   ├── host.bat            -- Batch launcher for the Python host
│   └── install_host.py     -- Registry installer for native messaging manifest
├── icons/                  -- Application and website icons (PNG, ICO, ICNS)
├── docs/                   -- Documentation screenshots and assets
│   └── screenshots/        -- UI screenshots
├── tests/                  -- Unit tests
│   └── test_downloader.py  -- Download engine tests
├── website/                -- Next.js 14 official website
│   └── src/
│       ├── app/            -- App Router pages and layouts
│       └── components/     -- UI components and sections
├── README.md               -- Project overview and quick start
├── CHANGELOG.md            -- Release history
├── CONTRIBUTING.md         -- This file
├── LICENSE                 -- MIT License
└── requirements.txt        -- Python dependencies
```

---

## Coding Style

### Python
- Follow [PEP 8](https://pep8.org/) with 100-character line length.
- Use type hints on public methods and functions.
- Prefer `pathlib.Path` over `os.path` for path operations.
- Use f-strings for string formatting.
- Docstrings for all public classes and methods.
- Imports ordered: stdlib → third-party → local.

### TypeScript / Next.js
- Use functional components with React hooks.
- Tailwind CSS utility classes (no custom CSS unless necessary).
- TypeScript strict mode is enabled.
- Components are organised as `sections/` (page sections) and `ui/` (reusable primitives).

### JavaScript (Browser Extensions)
- ES2020+ syntax.
- Minimal dependencies (vanilla JS, no framework).
- Consistent formatting with 2-space indentation.

---

## Testing

```bash
# Run existing tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_downloader.py -v
```

Before submitting a PR, verify:
- All existing tests pass.
- New code is covered by tests where feasible.
- The desktop application launches without errors: `python main.py`.

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add clipboard monitoring for automatic URL detection
fix: handle zero-byte Content-Length responses gracefully
docs: update installation guide for Python 3.12
refactor: extract segment allocation logic into allocator.py
chore: bump PyQt6 dependency to 6.6+
```

---

## Review Process

1. A maintainer will review your PR within 1–3 business days.
2. Automated checks (if configured) will validate formatting and tests.
3. Address review feedback — push additional commits to your branch.
4. Once approved, a maintainer will squash-merge your PR.

---

## Questions?

- Open a [GitHub Discussion](https://github.com/test-bit-sys/DLite/discussions) for questions about contributing.
- For bugs and features, use the [Issue Tracker](https://github.com/test-bit-sys/DLite/issues).

Thank you for helping make DLite the best open-source download manager!