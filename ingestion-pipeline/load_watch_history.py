import argparse
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime

from parse_takeout_history import parse_watch_history
from db import get_connection


from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

MELBOURNE_TZ = ZoneInfo("Australia/Melbourne")


def normalise_timestamp(timestamp: str) -> datetime:
    if not timestamp:
        raise ValueError("Missing timestamp")

    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        if parsed.tzinfo is not None:
            return parsed.astimezone(MELBOURNE_TZ).replace(tzinfo=None)

        return parsed
    except ValueError:
        pass

    try:
        cleaned = timestamp.replace("UTC", "GMT")
        parsed = parsedate_to_datetime(cleaned)

        if parsed.tzinfo is not None:
            return parsed.astimezone(MELBOURNE_TZ).replace(tzinfo=None)

        return parsed
    except Exception:
        pass

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
        INSERT INTO profiles (
            profile_id,
            display_name,
            profile_type,
            tenant_id,
            created_at
        )
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (profile_id) DO NOTHING
        """,
        (
            profile_id,
            "Uploaded Profile" if profile_id != "profile_self" else "Demo Profile",
            "personal_export",
            "default_tenant",
        ),
    )


def insert_events(events: list[dict], source_override: str | None = None):
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
                        watched_at = normalise_timestamp(event["watched_at"])

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
                            ON CONFLICT DO NOTHING
                            """,
                            (
                                event["profile_id"],
                                event["video_id"],
                                watched_at,
                                source_override or event.get("source") or "google_takeout",
                                event.get("raw_title"),
                                event.get("raw_url"),
                            ),
                        )

                        inserted += cursor.rowcount

                    except Exception as error:
                        skipped += 1
                        print(f"Skipping event due to error: {error}")
                        print(f"Problem event: {event}")

    finally:
        connection.close()

    return inserted, skipped


def update_import_job(import_job_id: str | None, total_events: int, inserted_events: int, skipped_events: int):
    if not import_job_id:
        return

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE import_jobs
                    SET total_events = %s,
                        inserted_events = %s,
                        error_message = NULL
                    WHERE import_job_id = %s
                    """,
                    (
                        total_events,
                        inserted_events,
                        import_job_id,
                    ),
                )
    finally:
        connection.close()


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("positional_input_file", nargs="?")
    parser.add_argument("positional_profile_id", nargs="?")

    parser.add_argument("--input-file", dest="input_file")
    parser.add_argument("--profile-id", dest="profile_id")
    parser.add_argument("--source", default=None)
    parser.add_argument("--import-job-id", default=None)

    args = parser.parse_args()

    input_file = args.input_file or args.positional_input_file
    profile_id = args.profile_id or args.positional_profile_id or "profile_self"

    if not input_file:
        raise RuntimeError(
            "Usage: python load_watch_history.py --input-file <path> --profile-id <profile_id>"
        )

    return input_file, profile_id, args.source, args.import_job_id


def main():
    input_file, profile_id, source, import_job_id = parse_args()

    events = parse_watch_history(input_file, profile_id=profile_id)

    print(f"Parsed {len(events)} valid watch events")

    if events:
        print("Sample event:")
        print(events[0])

    inserted, skipped = insert_events(events, source_override=source)

    update_import_job(
        import_job_id=import_job_id,
        total_events=len(events),
        inserted_events=inserted,
        skipped_events=skipped,
    )

    print(f"Inserted: {inserted}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()