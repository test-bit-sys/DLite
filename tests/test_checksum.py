import tempfile
import os
import hashlib
from engine.checksum import calculate_file_hashes, verify_checksum


def test_calculate_file_hashes():
    data = b"Hello DLite world! Testing cryptographic checksum integrity."
    expected_md5 = hashlib.md5(data).hexdigest()
    expected_sha1 = hashlib.sha1(data).hexdigest()
    expected_sha256 = hashlib.sha256(data).hexdigest()

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data)
        temp_path = f.name

    try:
        hashes = calculate_file_hashes(temp_path)
        assert hashes["md5"] == expected_md5
        assert hashes["sha1"] == expected_sha1
        assert hashes["sha256"] == expected_sha256
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_verify_checksum():
    data = b"Verify this content specifically."
    expected_sha256 = hashlib.sha256(data).hexdigest()

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data)
        temp_path = f.name

    try:
        # Exact match
        is_valid = verify_checksum(temp_path, expected_sha256)
        assert is_valid is True

        # Case-insensitive match
        is_valid_upper = verify_checksum(temp_path, expected_sha256.upper())
        assert is_valid_upper is True

        # Mismatched hash
        bad_hash = "a" * 64
        is_valid_bad = verify_checksum(temp_path, bad_hash)
        assert is_valid_bad is False
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
