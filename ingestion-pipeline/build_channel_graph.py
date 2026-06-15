import argparse
from collections import defaultdict
from datetime import timedelta

from db import get_connection


def fetch_profile_events(profile_id: str):
    query = """
        SELECT
            r.video_id,
            r.watched_at,
            y.channel_id,
            y.channel_title
        FROM raw_watch_events r
        JOIN youtube_videos y
            ON y.video_id = r.video_id
        WHERE r.profile_id = %s
          AND y.channel_id IS NOT NULL
        ORDER BY r.watched_at ASC
    """

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (profile_id,))
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        connection.close()


def calculate_channel_stats(events):
    stats = {}

    for event in events:
        channel_id = event["channel_id"]

        if channel_id not in stats:
            stats[channel_id] = {
                "channel_id": channel_id,
                "channel_title": event["channel_title"],
                "watch_count": 0,
                "video_ids": set(),
                "first_watched_at": event["watched_at"],
                "last_watched_at": event["watched_at"],
            }

        row = stats[channel_id]
        row["watch_count"] += 1
        row["video_ids"].add(event["video_id"])
        row["first_watched_at"] = min(row["first_watched_at"], event["watched_at"])
        row["last_watched_at"] = max(row["last_watched_at"], event["watched_at"])

    return stats


def calculate_channel_edges(events, session_gap_minutes: int):
    edges = {}
    max_gap = timedelta(minutes=session_gap_minutes)

    previous = None

    for current in events:
        if previous is None:
            previous = current
            continue

        gap = current["watched_at"] - previous["watched_at"]

        same_channel = previous["channel_id"] == current["channel_id"]
        same_session = gap >= timedelta(seconds=0) and gap <= max_gap

        if same_session and not same_channel:
            key = (previous["channel_id"], current["channel_id"])

            if key not in edges:
                edges[key] = {
                    "source_channel_id": previous["channel_id"],
                    "target_channel_id": current["channel_id"],
                    "source_channel_title": previous["channel_title"],
                    "target_channel_title": current["channel_title"],
                    "transition_count": 0,
                    "first_transition_at": current["watched_at"],
                    "last_transition_at": current["watched_at"],
                }

            edge = edges[key]
            edge["transition_count"] += 1
            edge["first_transition_at"] = min(edge["first_transition_at"], current["watched_at"])
            edge["last_transition_at"] = max(edge["last_transition_at"], current["watched_at"])

        previous = current

    return edges


def save_channel_stats(profile_id: str, stats: dict):
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM profile_channel_stats WHERE profile_id = %s",
                    (profile_id,),
                )

                for row in stats.values():
                    cursor.execute(
                        """
                        INSERT INTO profile_channel_stats (
                            profile_id,
                            channel_id,
                            channel_title,
                            watch_count,
                            unique_video_count,
                            first_watched_at,
                            last_watched_at,
                            calculated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """,
                        (
                            profile_id,
                            row["channel_id"],
                            row["channel_title"],
                            row["watch_count"],
                            len(row["video_ids"]),
                            row["first_watched_at"],
                            row["last_watched_at"],
                        ),
                    )
    finally:
        connection.close()


def save_channel_edges(profile_id: str, edges: dict):
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM profile_channel_edges WHERE profile_id = %s",
                    (profile_id,),
                )

                for row in edges.values():
                    cursor.execute(
                        """
                        INSERT INTO profile_channel_edges (
                            profile_id,
                            source_channel_id,
                            target_channel_id,
                            source_channel_title,
                            target_channel_title,
                            transition_count,
                            first_transition_at,
                            last_transition_at,
                            calculated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """,
                        (
                            profile_id,
                            row["source_channel_id"],
                            row["target_channel_id"],
                            row["source_channel_title"],
                            row["target_channel_title"],
                            row["transition_count"],
                            row["first_transition_at"],
                            row["last_transition_at"],
                        ),
                    )
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--session-gap-minutes", type=int, default=120)

    args = parser.parse_args()

    print(f"Building channel graph for profile: {args.profile_id}")

    events = fetch_profile_events(args.profile_id)

    print(f"Fetched events with channel metadata: {len(events)}")

    if not events:
        print("No channel metadata found. Run ingest_youtube_metadata.py first.")
        return

    stats = calculate_channel_stats(events)
    edges = calculate_channel_edges(
        events,
        session_gap_minutes=args.session_gap_minutes,
    )

    save_channel_stats(args.profile_id, stats)
    save_channel_edges(args.profile_id, edges)

    print(f"Saved channel nodes: {len(stats)}")
    print(f"Saved channel edges: {len(edges)}")


if __name__ == "__main__":
    main()