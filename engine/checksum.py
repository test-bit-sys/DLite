import hashlib
import os
from typing import Dict


def calculate_file_hashes(filepath: str, chunk_size: int = 128 * 1024) -> Dict[str, str]:
    """Calculate MD5, SHA-1, and SHA-256 in a single streaming pass without high memory usage."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    h_md5 = hashlib.md5()
    h_sha1 = hashlib.sha1()
    h_sha256 = hashlib.sha256()

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h_md5.update(chunk)
            h_sha1.update(chunk)
            h_sha256.update(chunk)

    return {
        "md5": h_md5.hexdigest().lower(),
        "sha1": h_sha1.hexdigest().lower(),
        "sha256": h_sha256.hexdigest().lower(),
    }


def verify_checksum(filepath: str, expected_hash: str, algo: str = "auto") -> bool:
    """
    Verify whether the file matches expected_hash.
    If algo is 'auto', determines the algorithm based on hash string length:
      - 32 chars: MD5
      - 40 chars: SHA-1
      - 64 chars: SHA-256
    """
    expected = expected_hash.strip().lower()
    if not expected:
        return True

    if algo == "auto":
        length = len(expected)
        if length == 32:
            algo = "md5"
        elif length == 40:
            algo = "sha1"
        elif length == 64:
            algo = "sha256"
        else:
            algo = "sha256"

    hashes = calculate_file_hashes(filepath)
    actual = hashes.get(algo.lower(), "")
    return actual == expected
