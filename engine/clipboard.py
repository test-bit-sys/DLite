"""
DLite Clipboard & URL Inspector
Provides URL parsing and downloadable file heuristics for clipboard monitoring
and automatic link detection.
"""
import re
from urllib.parse import urlparse

# Extensions commonly associated with direct downloadable assets
DOWNLOADABLE_EXTENSIONS = {
    # Archives & Compressed files
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab", "tgz",
    "z", "dmg", "pkg", "deb", "rpm", "zst", "cpio",
    # Executables & Installers
    "exe", "msi", "apk", "appimage", "bin", "run", "cmd", "bat", "jar",
    # Video & Media
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "ts",
    "mpg", "mpeg", "vob", "3gp", "ogv",
    # Audio
    "mp3", "wav", "flac", "aac", "ogg", "wma", "m4a", "opus", "alac", "aiff",
    # Documents & Books
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "epub", "mobi",
    "azw3", "djvu", "csv", "rtf", "odt", "ods", "odp",
    # Images & Artwork
    "jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "ico", "tiff", "psd",
    # Disk Images & Virtual Machines
    "img", "vmdk", "vdi", "qcow2", "rom", "nsp", "xci", "raw",
}


def is_downloadable_url(url: str, custom_extensions: set[str] | None = None) -> bool:
    """
    Determine if a string is a valid web URL likely pointing to a downloadable file.

    Checks:
      1. Valid protocol (http://, https://, ftp://).
      2. Direct path extension matching known file types.
      3. Query parameter indicators (e.g. ?download=1, ?dl=1, ?format=mp4, ?file=data.zip).
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("ftp://")):
        return False

    # Prevent matching ridiculously long or garbage text
    if len(url) > 2048 or " " in url or "\n" in url or "\t" in url:
        return False

    allowed = custom_extensions if custom_extensions is not None else DOWNLOADABLE_EXTENSIONS

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Check the path component
    path = parsed.path.lower()
    if "." in path:
        ext = path.rsplit(".", 1)[-1]
        ext = re.sub(r"[^a-z0-9]", "", ext)
        if ext in allowed:
            return True

    # Check query component for download hints
    query = parsed.query.lower()
    if query:
        # Check if query contains an explicit file parameter with known extension
        for ext in allowed:
            if f".{ext}" in query or f"format={ext}" in query:
                return True

        # Common direct download query parameters from cloud drives (Google Drive, Dropbox, OneDrive, Nextcloud)
        download_flags = ("download=1", "export=download", "dl=1", "action=download")
        if any(flag in query for flag in download_flags):
            return True

    return False


def extract_urls_from_text(text: str) -> list[str]:
    """Extract all valid HTTP/HTTPS/FTP URLs from arbitrary text."""
    if not text or not isinstance(text, str):
        return []

    # Regex matching URLs
    pattern = r'(?:https?|ftp)://[^\s<>"\']+'
    matches = re.findall(pattern, text)
    valid_urls = []
    for m in matches:
        cleaned = m.rstrip(".,;!?'\"()[]{}")
        if cleaned not in valid_urls:
            valid_urls.append(cleaned)
    return valid_urls
