# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of DLite seriously. If you believe you have found a
security vulnerability, please **do not open a public GitHub issue**.

Instead, report it privately using one of these channels:

- **GitHub Security Advisories** (preferred): use
  ["Report a vulnerability"](https://github.com/test-bit-sys/DLite/security/advisories/new)
  on the repository.
- **Email**: [safouaneescrow@gmail.com](mailto:safouaneescrow@gmail.com)

Please include:

1. A description of the issue and its potential impact
2. Step-by-step instructions or a proof of concept
3. Your OS version and DLite version
4. Any possible mitigations you have identified

### What to expect

- **Acknowledgement** within 72 hours
- An assessment and a fix timeline within 7 days
- Credit in the release notes (unless you prefer to remain anonymous)

## Scope

The following are in scope:

- The download engine (`engine/`), the GUI (`gui/`), the entry point (`main.py`)
- The native messaging host (`native_host/`) and the loopback TCP listener
- The browser extensions (`browser-extension/`)

The marketing website (`website/`) is out of scope except for issues that
leak credentials or allow account impersonation.

## Best practices for users

- Only download DLite from the official
  [GitHub Releases](https://github.com/test-bit-sys/DLite/releases) page.
- The app's browser integration listens on `127.0.0.1` (loopback) only —
  it is never exposed to the network.
