import os
import time
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

from db import get_connection

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def parse_youtube_datetime(value: str | None):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def safe_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def chunked(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def get_unfetched_video_ids(limit: int | None = None) -> list[str]:
    """
    Gets video IDs from raw_watch_events that are not already present in youtube_videos.
    """
    query = """
        SELECT DISTINCT r.video_id
        FROM raw_watch_events r
        LEFT JOIN youtube_videos y
            ON r.video_id = y.video_id
        WHERE y.video_id IS NULL
        ORDER BY r.video_id
    """

    if limit:
        query += " LIMIT %s"

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                if limit:
                    cursor.execute(query, (limit,))
                else:
                    cursor.execute(query)

                return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def fetch_metadata_batch(video_ids: list[str]) -> list[dict]:
    if not API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY in .env")

    params = {
        "part": "snippet,statistics,contentDetails,topicDetails",
        "id": ",".join(video_ids),
        "key": API_KEY,
    }

    response = requests.get(VIDEOS_URL, params=params, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"YouTube API request failed. "
            f"Status={response.status_code}, Body={response.text}"
        )

    payload = response.json()
    rows = []

    for item in payload.get("items", []):
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})
        topic_details = item.get("topicDetails", {})

        thumbnails = snippet.get("thumbnails", {})
        high_thumbnail = thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}

        rows.append({
            "video_id": item.get("id"),
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "channel_id": snippet.get("channelId"),
            "channel_title": snippet.get("channelTitle"),
            "published_at": parse_youtube_datetime(snippet.get("publishedAt")),
            "tags": "|".join(snippet.get("tags", [])),
            "category_id": snippet.get("categoryId"),
            "duration": content_details.get("duration"),
            "view_count": safe_int(statistics.get("viewCount")),
            "like_count": safe_int(statistics.get("likeCount")),
            "comment_count": safe_int(statistics.get("commentCount")),
            "topic_categories": "|".join(topic_details.get("topicCategories", [])),
            "thumbnail_url": high_thumbnail.get("url"),
        })

    return rows


def upsert_video_metadata(rows: list[dict]) -> int:
    if not rows:
        return 0

    connection = get_connection()
    inserted = 0

    try:
        with connection:
            with connection.cursor() as cursor:
                for row in rows:
                    cursor.execute(
                        """
                        INSERT INTO youtube_videos (
                            video_id,
                            title,
                            description,
                            channel_id,
                            channel_title,
                            published_at,
                            tags,
                            category_id,
                            duration,
                            view_count,
                            like_count,
                            comment_count,
                            topic_categories,
                            thumbnail_url,
                            collected_at
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (video_id)
                        DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            channel_id = EXCLUDED.channel_id,
                            channel_title = EXCLUDED.channel_title,
                            published_at = EXCLUDED.published_at,
                            tags = EXCLUDED.tags,
                            category_id = EXCLUDED.category_id,
                            duration = EXCLUDED.duration,
                            view_count = EXCLUDED.view_count,
                            like_count = EXCLUDED.like_count,
                            comment_count = EXCLUDED.comment_count,
                            topic_categories = EXCLUDED.topic_categories,
                            thumbnail_url = EXCLUDED.thumbnail_url,
                            collected_at = CURRENT_TIMESTAMP
                        """,
                        (
                            row["video_id"],
                            row["title"],
                            row["description"],
                            row["channel_id"],
                            row["channel_title"],
                            row["published_at"],
                            row["tags"],
                            row["category_id"],
                            row["duration"],
                            row["view_count"],
                            row["like_count"],
                            row["comment_count"],
                            row["topic_categories"],
                            row["thumbnail_url"],
                        ),
                    )
                    inserted += 1

    finally:
        connection.close()

    return inserted


def main():
    video_ids = get_unfetched_video_ids()

    print(f"Found {len(video_ids)} unique videos missing metadata")

    if not video_ids:
        print("No work to do.")
        return

    total_saved = 0
    total_requested = 0

    for batch in chunked(video_ids, 50):
        total_requested += len(batch)

        print(f"Fetching batch of {len(batch)} videos...")

        try:
            rows = fetch_metadata_batch(batch)
            saved = upsert_video_metadata(rows)
            total_saved += saved

            missing_count = len(batch) - len(rows)

            print(
                f"Requested={len(batch)}, returned={len(rows)}, "
                f"saved={saved}, unavailable={missing_count}"
            )

        except Exception as error:
            print(f"Batch failed: {error}")

        time.sleep(0.2)

    print("Metadata ingestion complete")
    print(f"Total requested: {total_requested}")
    print(f"Total saved: {total_saved}")


if __name__ == "__main__":
    main()