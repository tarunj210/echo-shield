import sys
from datetime import datetime
from email.utils import parsedate_to_datetime

from parse_takeout_history import parse_watch_history
from db import get_connection


def normalise_timestamp(timestamp: str) -> datetime:
    """
    Handles both:
    - JSON timestamps: 2026-06-01T10:30:00.000Z
    - HTML timestamps: Jun 1, 2026, 10:30:00 PM GMT+10
    """
    if not timestamp:
        raise ValueError("Missing timestamp")

    # JSON format
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        pass

    # HTML format from Google Takeout
    try:
        cleaned = timestamp.replace("UTC", "GMT")
        return parsedate_to_datetime(cleaned)
    except Exception:
        pass

    # Last fallback for common Takeout variants
    formats = [
        "%b %d, %Y, %I:%M:%S %p %Z",
        "%d %b %Y, %H:%M:%S %Z",
        "%d %b %Y, %I:%M:%S %p %Z",
        "%b %d, %Y, %H:%M:%S %Z",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            continue

    raise ValueError(f"Could not parse timestamp: {timestamp}")


def ensure_profile(cursor, profile_id: str):
    cursor.execute(
        """
        INSERT INTO profiles (profile_id, display_name, profile_type)
        VALUES (%s, %s, %s)
        ON CONFLICT (profile_id) DO NOTHING
        """,
        (profile_id, "Demo Profile", "personal_export"),
    )


def insert_events(events: list[dict]):
    connection = get_connection()

    inserted = 0
    skipped = 0

    try:
        with connection:
            with connection.cursor() as cursor:
                if not events:
                    return inserted, skipped

                profile_id = events[0]["profile_id"]
                ensure_profile(cursor, profile_id)

                for event in events:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO raw_watch_events (
                                profile_id,
                                video_id,
                                watched_at,
                                source,
                                raw_title,
                                raw_url
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                event["profile_id"],
                                event["video_id"],
                                normalise_timestamp(event["watched_at"]),
                                event["source"],
                                event["raw_title"],
                                event["raw_url"],
                            ),
                        )
                        inserted += 1

                    except Exception as error:
                        skipped += 1
                        print(f"Skipping event due to error: {error}")
                        print(f"Problem event: {event}")

    finally:
        connection.close()

    return inserted, skipped


def main():
    if len(sys.argv) < 2:
        raise RuntimeError(
            "Usage: python load_watch_history.py ../data/raw/watch-history.html"
        )

    file_path = sys.argv[1]
    profile_id = sys.argv[2] if len(sys.argv) >= 3 else "profile_self"

    events = parse_watch_history(file_path, profile_id=profile_id)

    print(f"Parsed {len(events)} valid watch events")

    if events:
        print("Sample event:")
        print(events[0])

    inserted, skipped = insert_events(events)

    print(f"Inserted: {inserted}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()