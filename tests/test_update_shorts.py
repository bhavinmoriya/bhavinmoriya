from datetime import date
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from update_shorts import is_short, parse_duration, target_date_from_arg, transform_video
from zoneinfo import ZoneInfo


def test_parse_duration():
    assert parse_duration("PT42S") == 42
    assert parse_duration("PT1M05S") == 65
    assert parse_duration("PT2M03S") == 123


def test_short_when_channel_is_configured_as_shorts_only():
    video = {
        "contentDetails": {"duration": "PT45S"}
    }
    assert is_short(video, {
        "max_duration_seconds": 180,
        "assume_all_uploads_are_shorts": True,
    }) is True


def test_mixed_channel_requires_explicit_short_mode():
    video = {
        "contentDetails": {"duration": "PT45S"}
    }
    assert is_short(video, {
        "max_duration_seconds": 180,
        "assume_all_uploads_are_shorts": False,
    }) is False


def test_long_video_is_not_short():
    video = {
        "contentDetails": {
            "duration": "PT3M01S",
            "dimension": {"width": "1080", "height": "1920"},
        }
    }
    assert is_short(video, {"max_duration_seconds": 180}) is False


def test_duration_safeguard():
    video = {
        "contentDetails": {"duration": "PT3M01S"}
    }
    assert is_short(video, {
        "max_duration_seconds": 180,
        "assume_all_uploads_are_shorts": True,
    }) is False


def test_target_date():
    tz = ZoneInfo("Europe/Berlin")
    assert target_date_from_arg("2026-09-29", tz) == date(2026, 9, 29)


def test_transform_video():
    raw = {
        "id": "abc123",
        "snippet": {
            "title": "Test Short",
            "publishedAt": "2026-09-29T10:00:00Z",
            "thumbnails": {"high": {"url": "https://example.com/a.jpg"}},
        },
        "contentDetails": {"duration": "PT1M02S"},
        "statistics": {"viewCount": "1234"},
    }
    video = transform_video(raw)
    assert video.video_id == "abc123"
    assert video.view_count == 1234
    assert video.duration_seconds == 62
    assert video.youtube_url.endswith("/abc123")
