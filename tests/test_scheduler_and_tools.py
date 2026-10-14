from datetime import datetime, time as dtime
from engine.config import config
from engine.scheduler import DownloadScheduler, is_in_time_window, parse_time_str
from engine.clipboard import is_downloadable_url, extract_urls_from_text
from engine.pattern_generator import expand_pattern


def test_time_window():
    # Daytime window
    assert is_in_time_window(dtime(12, 0), dtime(9, 0), dtime(18, 0)) is True
    assert is_in_time_window(dtime(8, 59), dtime(9, 0), dtime(18, 0)) is False
    assert is_in_time_window(dtime(18, 1), dtime(9, 0), dtime(18, 0)) is False

    # Overnight window (22:00 to 06:00)
    assert is_in_time_window(dtime(23, 30), dtime(22, 0), dtime(6, 0)) is True
    assert is_in_time_window(dtime(3, 0), dtime(22, 0), dtime(6, 0)) is True
    assert is_in_time_window(dtime(12, 0), dtime(22, 0), dtime(6, 0)) is False


def test_parse_time_str():
    t1 = parse_time_str("02:30")
    assert t1.hour == 2 and t1.minute == 30 and t1.second == 0

    t2 = parse_time_str("15:45:20")
    assert t2.hour == 15 and t2.minute == 45 and t2.second == 20


def test_scheduler_throttling():
    sched = DownloadScheduler()

    # Save original settings
    orig_sched = config.get("scheduler_enabled", False)
    orig_throttle = config.get("scheduler_throttle_enabled", False)
    orig_speed = config.get("speed_limit_kbps", 0)

    try:
        config.set("scheduler_enabled", True)
        config.set("scheduler_throttle_enabled", True)
        config.set("scheduler_throttle_start", "08:00")
        config.set("scheduler_throttle_end", "17:00")
        config.set("scheduler_throttle_rate_kbps", 300)
        config.set("speed_limit_kbps", 0)

        # Inside window
        now_inside = datetime(2026, 10, 14, 10, 0, 0)
        sched.check(now_inside)
        assert config.get("speed_limit_kbps") == 300
        assert sched._throttled_by_scheduler is True

        # Outside window
        now_outside = datetime(2026, 10, 14, 19, 0, 0)
        sched.check(now_outside)
        assert config.get("speed_limit_kbps") == 0
        assert sched._throttled_by_scheduler is False
    finally:
        config.set("scheduler_enabled", orig_sched)
        config.set("scheduler_throttle_enabled", orig_throttle)
        config.set("speed_limit_kbps", orig_speed)


def test_is_downloadable_url():
    # Direct file extensions
    assert is_downloadable_url("https://example.com/file.zip") is True
    assert is_downloadable_url("http://cdn.site.org/video.mp4") is True
    assert is_downloadable_url("https://archive.org/os.iso") is True
    assert is_downloadable_url("https://download.com/setup.exe") is True

    # Cloud query patterns
    assert is_downloadable_url("https://drive.google.com/uc?id=123&export=download") is True
    assert is_downloadable_url("https://dropbox.com/s/xyz/sample.pdf?dl=1") is True

    # Regular web pages
    assert is_downloadable_url("https://github.com/test-bit-sys/DLite") is False
    assert is_downloadable_url("https://en.wikipedia.org/wiki/Download_manager") is False
    assert is_downloadable_url("not a url") is False


def test_extract_urls_from_text():
    text = "Here are links: https://example.com/one.zip and http://test.org/two.iso! Check them out."
    urls = extract_urls_from_text(text)
    assert "https://example.com/one.zip" in urls
    assert "http://test.org/two.iso" in urls
    assert len(urls) == 2


def test_expand_pattern_numeric():
    # Padded numeric
    urls = expand_pattern("https://site.com/img_[01-05].png")
    assert len(urls) == 5
    assert urls[0] == "https://site.com/img_01.png"
    assert urls[4] == "https://site.com/img_05.png"

    # With step
    urls_step = expand_pattern("https://site.com/chunk_[1-7:2].bin")
    assert urls_step == [
        "https://site.com/chunk_1.bin",
        "https://site.com/chunk_3.bin",
        "https://site.com/chunk_5.bin",
        "https://site.com/chunk_7.bin",
    ]


def test_expand_pattern_alpha():
    urls = expand_pattern("https://site.com/part_[a-d].zip")
    assert urls == [
        "https://site.com/part_a.zip",
        "https://site.com/part_b.zip",
        "https://site.com/part_c.zip",
        "https://site.com/part_d.zip",
    ]
