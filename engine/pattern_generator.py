"""
DLite Batch URL Pattern Generator
Expands URL templates containing range expressions like [01-20] or [a-z] into
lists of individual download URLs.
"""
import itertools
import re
from urllib.parse import urlparse

# Matches expressions like [01-20], [1-100:2], [a-z], [A-F]
PATTERN_REGEX = re.compile(r"\[([a-zA-Z0-9]+)-([a-zA-Z0-9]+)(?::([0-9]+))?\]")


def expand_pattern(pattern: str, max_items: int = 1000) -> list[str]:
    """
    Expand a URL pattern into a list of URLs.

    Examples:
      - 'http://example.com/part_[01-05].rar' -> part_01.rar ... part_05.rar
      - 'http://example.com/page_[1-5:2].html' -> page_1.html, page_3.html, page_5.html
      - 'http://example.com/img_[a-c].jpg' -> img_a.jpg, img_b.jpg, img_c.jpg
      - 'http://example.com/s[1-2]_e[01-02].mp4' -> Cartesian product of ranges
    """
    pattern = pattern.strip()
    if not pattern:
        return []

    matches = list(PATTERN_REGEX.finditer(pattern))
    if not matches:
        return [pattern] if pattern.startswith(("http://", "https://", "ftp://")) else []

    # Generate values for each match
    replacement_groups = []
    for match in matches:
        start_raw, end_raw, step_raw = match.groups()
        step = int(step_raw) if step_raw else 1
        if step <= 0:
            step = 1

        # Check numeric range
        if start_raw.isdigit() and end_raw.isdigit():
            start_num = int(start_raw)
            end_num = int(end_raw)
            # Check if leading zero formatting is desired
            width = len(start_raw) if (start_raw.startswith("0") and len(start_raw) > 1) else 0

            if start_num <= end_num:
                values = [
                    f"{n:0{width}d}" if width else str(n)
                    for n in range(start_num, end_num + 1, step)
                ]
            else:
                values = [
                    f"{n:0{width}d}" if width else str(n)
                    for n in range(start_num, end_num - 1, -step)
                ]
            replacement_groups.append(values)

        # Check alphabetical character range
        elif len(start_raw) == 1 and len(end_raw) == 1 and start_raw.isalpha() and end_raw.isalpha():
            start_code = ord(start_raw)
            end_code = ord(end_raw)

            if start_code <= end_code:
                values = [chr(c) for c in range(start_code, end_code + 1, step)]
            else:
                values = [chr(c) for c in range(start_code, end_code - 1, -step)]
            replacement_groups.append(values)

        else:
            raise ValueError(f"Invalid range expression: {match.group(0)}")

    # Calculate total count to enforce safety bounds
    total_count = 1
    for grp in replacement_groups:
        total_count *= len(grp)
        if total_count > max_items:
            raise ValueError(
                f"Generated pattern exceeds safety limit of {max_items} URLs (total: {total_count}). "
                "Please narrow your range."
            )

    # Perform Cartesian substitution
    results = []
    for combination in itertools.product(*replacement_groups):
        expanded = pattern
        # Replace matches from right to left so indices don't shift
        for match, val in zip(reversed(matches), reversed(combination), strict=True):
            expanded = expanded[:match.start()] + val + expanded[match.end():]
        results.append(expanded)

    return results


def extract_filename_from_url(url: str) -> str:
    """Derive clean file name from an expanded URL."""
    path = urlparse(url).path
    filename = path.rsplit("/", 1)[-1].split("?")[0] if path else ""
    return filename or "download.bin"
