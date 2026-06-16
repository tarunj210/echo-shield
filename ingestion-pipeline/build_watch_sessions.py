import argparse
from collections import Counter
from datetime import timedelta

from db import get_connection


def fetch_events(profile_id: str):
    query = """
        SELECT
            r.event_id,
            r.profile_id,
            r.video_id,
            r.watched_at,
            COALESCE(y.channel_id, 'unknown') AS channel_id,
            COALESCE(y.channel_title, 'Unknown Channel') AS channel_title
        FROM raw_watch_events r
        LEFT JOIN youtube_videos y
            ON y.video_id = r.video_id
        WHERE r.profile_id = %s
        ORDER BY r.watched_at ASC, r.event_id ASC
    """

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (profile_id,))
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        connection.close()


def build_sessions(
    profile_id: str,
    events: list[dict],
    session_gap_minutes: int,
    max_session_duration_minutes: int,
    max_videos_per_session: int,
):
    if not events:
        return [], []

    max_gap = timedelta(minutes=session_gap_minutes)
    max_duration = timedelta(minutes=max_session_duration_minutes)

    sessions = []
    assignments = []

    current_session_events = []
    previous_event = None
    session_index = 0

    def close_session(session_events, index):
        if not session_events:
            return

        session_start = session_events[0]["watched_at"]
        session_end = session_events[-1]["watched_at"]
        session_id = f"{profile_id}_session_{index:05d}"

        channel_counts = Counter(
            event["channel_title"] for event in session_events
        )

        dominant_channel_title = channel_counts.most_common(1)[0][0]
        unique_channel_count = len(set(event["channel_id"] for event in session_events))
        total_duration_minutes = int((session_end - session_start).total_seconds() // 60)

        sessions.append(
            {
                "session_id": session_id,
                "profile_id": profile_id,
                "session_index": index,
                "session_start": session_start,
                "session_end": session_end,
                "video_count": len(session_events),
                "unique_channel_count": unique_channel_count,
                "dominant_channel_title": dominant_channel_title,
                "total_duration_minutes": total_duration_minutes,
            }
        )

        previous_in_session = None

        for sequence_index, event in enumerate(session_events, start=1):
            minutes_since_previous = None

            if previous_in_session is not None:
                minutes_since_previous = int(
                    (event["watched_at"] - previous_in_session["watched_at"]).total_seconds() // 60
                )

            assignments.append(
                {
                    "event_id": event["event_id"],
                    "profile_id": profile_id,
                    "session_id": session_id,
                    "sequence_in_session": sequence_index,
                    "minutes_since_previous": minutes_since_previous,
                }
            )

            previous_in_session = event

    for event in events:
        if previous_event is None:
            session_index += 1
            current_session_events = [event]
            previous_event = event
            continue

        gap = event["watched_at"] - previous_event["watched_at"]
        current_session_start = current_session_events[0]["watched_at"]
        current_duration = event["watched_at"] - current_session_start

        gap_break = gap > max_gap or gap.total_seconds() < 0
        duration_break = current_duration > max_duration
        count_break = len(current_session_events) >= max_videos_per_session

        # Optional: prevents one session from crossing into a new date.
        date_break = event["watched_at"].date() != previous_event["watched_at"].date()

        should_start_new_session = (
            gap_break
            or duration_break
            or count_break
            or date_break
        )

        if should_start_new_session:
            close_session(current_session_events, session_index)
            session_index += 1
            current_session_events = [event]
        else:
            current_session_events.append(event)

        previous_event = event

    close_session(current_session_events, session_index)

    return sessions, assignments


def save_sessions(profile_id: str, sessions: list[dict], assignments: list[dict]):
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM watch_event_session_assignments
                    WHERE profile_id = %s
                    """,
                    (profile_id,),
                )

                cursor.execute(
                    """
                    DELETE FROM profile_watch_sessions
                    WHERE profile_id = %s
                    """,
                    (profile_id,),
                )

                for session in sessions:
                    cursor.execute(
                        """
                        INSERT INTO profile_watch_sessions (
                            session_id,
                            profile_id,
                            session_index,
                            session_start,
                            session_end,
                            video_count,
                            unique_channel_count,
                            dominant_channel_title,
                            total_duration_minutes,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """,
                        (
                            session["session_id"],
                            session["profile_id"],
                            session["session_index"],
                            session["session_start"],
                            session["session_end"],
                            session["video_count"],
                            session["unique_channel_count"],
                            session["dominant_channel_title"],
                            session["total_duration_minutes"],
                        ),
                    )

                for assignment in assignments:
                    cursor.execute(
                        """
                        INSERT INTO watch_event_session_assignments (
                            event_id,
                            profile_id,
                            session_id,
                            sequence_in_session,
                            minutes_since_previous
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            assignment["event_id"],
                            assignment["profile_id"],
                            assignment["session_id"],
                            assignment["sequence_in_session"],
                            assignment["minutes_since_previous"],
                        ),
                    )

    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--session-gap-minutes", type=int, default=30)
    parser.add_argument("--max-session-duration-minutes", type=int, default=180)
    parser.add_argument("--max-videos-per-session", type=int, default=80)

    args = parser.parse_args()

    print(f"Building watch sessions for profile: {args.profile_id}")
    print(f"Session gap: {args.session_gap_minutes} minutes")
    print(f"Max session duration: {args.max_session_duration_minutes} minutes")
    print(f"Max videos per session: {args.max_videos_per_session}")

    events = fetch_events(args.profile_id)

    print(f"Fetched events: {len(events)}")

    sessions, assignments = build_sessions(
        profile_id=args.profile_id,
        events=events,
        session_gap_minutes=args.session_gap_minutes,
        max_session_duration_minutes=args.max_session_duration_minutes,
        max_videos_per_session=args.max_videos_per_session,
    )

    save_sessions(args.profile_id, sessions, assignments)

    print(f"Saved sessions: {len(sessions)}")
    print(f"Saved assignments: {len(assignments)}")


if __name__ == "__main__":
    main()