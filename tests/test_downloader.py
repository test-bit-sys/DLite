import http.server
import os
import re
import socketserver
import threading
import time
from pathlib import Path

import pytest

from engine.config import config
from engine.downloader import Downloader
from engine.models import DownloadTask, DownloadStatus
from engine.queue_manager import QueueManager


class RangeCapableHandler(http.server.BaseHTTPRequestHandler):
    payload = b""

    def do_HEAD(self):
        if self.path == "/head-fail.bin":
            self.send_response(405)
            self.end_headers()
            return

        if self.path == "/redirect.bin":
            self.send_response(302)
            self.send_header("Location", "/file.bin")
            self.end_headers()
            return

        if self.path == "/disposition.bin":
            self.send_response(200)
            self.send_header("Content-Length", str(len(self.payload)))
            self.send_header("Content-Disposition", 'attachment; filename="correct_name.zip"')
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

    def do_GET(self):
        if self.path == "/redirect.bin":
            self.send_response(302)
            self.send_header("Location", "/file.bin")
            self.end_headers()
            return

        if self.path == "/disposition.bin":
            self.send_response(200)
            self.send_header("Content-Length", str(len(self.payload)))
            self.send_header("Content-Disposition", 'attachment; filename="correct_name.zip"')
            self.end_headers()
            self.wfile.write(self.payload)
            return

        range_header = self.headers.get("Range")
        if range_header:
            match = re.match(r"bytes=(\d+)-(\d+)", range_header)
            start, end = int(match.group(1)), int(match.group(2))
            chunk = self.payload[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(self.payload)}")
            self.send_header("Content-Length", str(len(chunk)))
            self.end_headers()
            # trickle the response so tests have a real window to pause/cancel in
            for offset in range(0, len(chunk), 32 * 1024):
                self.wfile.write(chunk[offset:offset + 32 * 1024])
                time.sleep(0.01)
        else:
            self.send_response(200)
            self.send_header("Content-Length", str(len(self.payload)))
            self.end_headers()
            self.wfile.write(self.payload)

    def log_message(self, format, *args):
        pass


def _wait_until(condition, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.01)
    raise TimeoutError("condition was never met")


@pytest.fixture(scope="module")
def test_server():
    RangeCapableHandler.payload = os.urandom(4 * 1024 * 1024)
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), RangeCapableHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/file.bin", RangeCapableHandler.payload
    server.shutdown()


def test_full_download_matches_source(test_server, tmp_path):
    url, payload = test_server
    config.set("max_segments", 4)

    task = DownloadTask(url=url, dest_path=str(tmp_path / "out.bin"))
    Downloader(task).run()

    assert task.status == DownloadStatus.COMPLETED
    assert task.supports_range is True
    assert len(task.segments) == 4
    assert (tmp_path / "out.bin").read_bytes() == payload


def test_pause_and_resume_preserves_data(test_server, tmp_path):
    url, payload = test_server
    task = DownloadTask(url=url, dest_path=str(tmp_path / "out2.bin"))
    downloader = Downloader(task)

    thread = threading.Thread(target=downloader.run)
    thread.start()
    _wait_until(lambda: task.downloaded_bytes > 0)
    downloader.pause()
    time.sleep(0.3)

    assert task.status == DownloadStatus.PAUSED
    assert 0 < task.downloaded_bytes < task.total_size

    downloader.resume()
    thread.join(timeout=10)

    assert task.status == DownloadStatus.COMPLETED
    assert (tmp_path / "out2.bin").read_bytes() == payload


def test_cancel_stops_the_download(test_server, tmp_path):
    url, _ = test_server
    task = DownloadTask(url=url, dest_path=str(tmp_path / "out3.bin"))
    downloader = Downloader(task)

    thread = threading.Thread(target=downloader.run)
    thread.start()
    _wait_until(lambda: task.downloaded_bytes > 0)
    downloader.cancel()
    thread.join(timeout=10)

    assert task.status == DownloadStatus.CANCELED


def test_head_fallback_downloads_correctly(test_server, tmp_path):
    url_base, payload = test_server
    url = url_base.replace("/file.bin", "/head-fail.bin")

    task = DownloadTask(url=url, dest_path=str(tmp_path / "fallback.bin"))
    Downloader(task).run()

    assert task.status == DownloadStatus.COMPLETED
    assert (tmp_path / "fallback.bin").read_bytes() == payload


def test_redirect_url_updated(test_server, tmp_path):
    url_base, payload = test_server
    url = url_base.replace("/file.bin", "/redirect.bin")

    task = DownloadTask(url=url, dest_path=str(tmp_path / "redirect.bin"))
    Downloader(task).run()

    assert task.status == DownloadStatus.COMPLETED
    assert task.url.endswith("/file.bin")
    assert (tmp_path / "redirect.bin").read_bytes() == payload


def test_content_disposition_filename(test_server, tmp_path):
    url_base, payload = test_server
    url = url_base.replace("/file.bin", "/disposition.bin")

    task = DownloadTask(url=url, dest_path=str(tmp_path / "guessed.bin"))
    Downloader(task).run()

    assert task.status == DownloadStatus.COMPLETED
    assert task.filename == "correct_name.zip"
    assert task.dest_path.endswith("correct_name.zip")
    assert os.path.exists(task.dest_path)
    assert Path(task.dest_path).read_bytes() == payload


def test_queue_controls_delegate_to_active_downloader():
    class FakeDownloader:
        def __init__(self):
            self.paused = False
            self.resumed = False
            self.canceled = False

        def pause(self):
            self.paused = True

        def resume(self):
            self.resumed = True

        def cancel(self):
            self.canceled = True

    manager = QueueManager()
    task = manager.add("http://example.test/file.bin", filename="file.bin")
    fake = FakeDownloader()
    manager._downloaders[task.id] = fake

    task.status = DownloadStatus.DOWNLOADING
    manager.pause(task.id)

    assert fake.paused is True
    assert task.status == DownloadStatus.PAUSED

    manager.resume(task.id)

    assert fake.resumed is True
    assert task.status == DownloadStatus.DOWNLOADING

    manager.cancel(task.id)

    assert fake.canceled is True
    assert task.status == DownloadStatus.CANCELED
