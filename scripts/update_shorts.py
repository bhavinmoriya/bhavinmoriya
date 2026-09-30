from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

API_BASE = "https://www.googleapis.com/youtube/v3"
ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "shorts" / "config.json"
OUTPUT_PATH = ROOT / "shorts" / "data" / "shorts.json"


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    published_at: str
    view_count: int
    duration_seconds: int
    thumbnail_url: str
    youtube_url: str


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_duration(value: str) -> int:
    # YouTube API duration is ISO 8601, normally PT#M#S / PT#H#M#S.
    import re
    match = re.fullmatch(
        r"PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?",
        value,
    )
    if not match:
        raise ValueError(f"Unsupported YouTube duration: {value}")
    return (
        int(match.group("h") or 0) * 3600
        + int(match.group("m") or 0) * 60
        + int(match.group("s") or 0)
    )


def api_get(client: httpx.Client, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    response = client.get(f"{API_BASE}/{endpoint}", params=params)
    response.raise_for_status()
    return response.json()


def get_channel(client: httpx.Client, api_key: str, channel_id: str) -> dict[str, Any]:
    data = api_get(
        client,
        "channels",
        {
            "part": "contentDetails,snippet",
            "id": channel_id,
            "key": api_key,
        },
    )
    if not data.get("items"):
        raise RuntimeError(f"No YouTube channel found for channel ID {channel_id!r}")
    return data["items"][0]


def get_uploads(
    client: httpx.Client,
    api_key: str,
    uploads_playlist_id: str,
    start_utc: datetime,
    end_utc: datetime,
    max_pages: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token: str | None = None

    for _ in range(max_pages):
        params = {
            "part": "snippet,contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": 50,
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        data = api_get(client, "playlistItems", params)

        for item in data.get("items", []):
            published = item.get("contentDetails", {}).get("videoPublishedAt") or item.get(
                "snippet", {}
            ).get("publishedAt")
            if not published:
                continue

            published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))

            if start_utc <= published_dt < end_utc:
                items.append(item)

            # Upload playlist is newest-first. Once items are older than the
            # target interval we can stop after finishing the current page.
            if published_dt < start_utc:
                return items

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return items


def get_video_details(
    client: httpx.Client,
    api_key: str,
    video_ids: list[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        data = api_get(
            client,
            "videos",
            {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(chunk),
                "key": api_key,
            },
        )
        result.extend(data.get("items", []))
    return result


def is_short(video: dict[str, Any], config: dict[str, Any]) -> bool:
    """Classify an upload for this channel's Shorts feed.

    The YouTube Data API does not expose a reliable public `isShort` flag or
    the video's aspect ratio in the video resource. Therefore, for a channel
    dedicated to Shorts, the safest API-only approach is to explicitly assume
    uploads are Shorts and apply a duration safeguard.
    """
    details = video.get("contentDetails", {})
    duration = parse_duration(details.get("duration", "PT0S"))

    if duration > int(config.get("max_duration_seconds", 180)):
        return False

    if config.get("assume_all_uploads_are_shorts", False):
        return True

    # If the channel also uploads long-form videos, the API alone cannot
    # reliably distinguish every Short from every vertical long-form upload.
    # In that mixed-channel case, require an explicit configuration decision.
    return False


def transform_video(video: dict[str, Any]) -> Video:
    snippet = video.get("snippet", {})
    stats = video.get("statistics", {})
    details = video.get("contentDetails", {})
    video_id = video["id"]

    return Video(
        video_id=video_id,
        title=snippet.get("title", "Untitled Short"),
        published_at=snippet.get("publishedAt", ""),
        view_count=int(stats.get("viewCount", 0)),
        duration_seconds=parse_duration(details.get("duration", "PT0S")),
        thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        youtube_url=f"https://www.youtube.com/shorts/{video_id}",
    )


def target_date_from_arg(value: str | None, tz: ZoneInfo) -> date:
    if value:
        return date.fromisoformat(value)
    return datetime.now(tz).date() - timedelta(days=1)


def build(target_date: date, config: dict[str, Any], api_key: str, channel_id: str) -> dict[str, Any]:
    tz = ZoneInfo(config.get("timezone", "Europe/Berlin"))
    start_local = datetime.combine(target_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)

    with httpx.Client(timeout=30.0) as client:
        channel = get_channel(client, api_key, channel_id)
        uploads_playlist_id = (
            channel["contentDetails"]["relatedPlaylists"]["uploads"]
        )
        upload_items = get_uploads(
            client,
            api_key,
            uploads_playlist_id,
            start_local.astimezone(timezone.utc),
            end_local.astimezone(timezone.utc),
            int(config.get("max_upload_playlist_pages", 5)),
        )

        ids = [
            item["contentDetails"]["videoId"]
            for item in upload_items
            if item.get("contentDetails", {}).get("videoId")
        ]
        details = get_video_details(client, api_key, ids) if ids else []

    shorts = [video for video in details if is_short(video, config)]
    videos = [transform_video(video) for video in shorts]
    videos.sort(key=lambda v: v.published_at)

    most_viewed = max(videos, key=lambda v: v.view_count) if videos else None

    return {
        "target_date": target_date.isoformat(),
        "timezone": config.get("timezone", "Europe/Berlin"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "videos": [asdict(v) for v in videos],
        "most_viewed": asdict(most_viewed) if most_viewed else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target local date in YYYY-MM-DD")
    args = parser.parse_args()

    api_key = os.environ.get("YOUTUBE_API_KEY")
    channel_id = os.environ.get("YOUTUBE_CHANNEL_ID")

    if not api_key:
        print("Missing YOUTUBE_API_KEY", file=sys.stderr)
        return 2
    if not channel_id:
        print("Missing YOUTUBE_CHANNEL_ID", file=sys.stderr)
        return 2

    config = load_config()
    tz = ZoneInfo(config.get("timezone", "Europe/Berlin"))
    target_date = target_date_from_arg(args.date, tz)
    payload = build(target_date, config, api_key, channel_id)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        f"Generated {OUTPUT_PATH}: {len(payload['videos'])} Shorts for "
        f"{payload['target_date']}"
    )
    if payload["most_viewed"]:
        print(
            f"Most viewed: {payload['most_viewed']['title']} "
            f"({payload['most_viewed']['view_count']} views)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
