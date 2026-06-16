import argparse
import re
import sys
import time
from typing import Any, Optional

from sentence_transformers import SentenceTransformer

from db import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item is not None)

    value = str(value)
    value = value.replace("|", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def build_content_text(row: dict) -> str:
    text = " ".join(
        [
            clean_text(row.get("title")),
            clean_text(row.get("description")),
            clean_text(row.get("tags")),
            clean_text(row.get("topic_categories")),
        ]
    ).strip()

    if text:
        return text

    return clean_text(row.get("video_id"))


def ensure_embedding_job(
    profile_id: str,
    embedding_job_id: Optional[str],
    batch_size: int,
) -> str:
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                if embedding_job_id:
                    cursor.execute(
                        """
                        SELECT embedding_job_id
                        FROM embedding_jobs
                        WHERE embedding_job_id = %s
                          AND profile_id = %s
                        """,
                        (embedding_job_id, profile_id),
                    )

                    row = cursor.fetchone()

                    if not row:
                        raise ValueError(
                            f"Embedding job {embedding_job_id} does not exist for profile {profile_id}"
                        )

                    return str(row[0])

                cursor.execute(
                    """
                    INSERT INTO embedding_jobs (
                        profile_id,
                        status,
                        total_videos,
                        embedded_videos,
                        failed_videos,
                        batch_size,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        %s,
                        'PENDING',
                        (
                            SELECT COUNT(DISTINCT video_id)
                            FROM raw_watch_events
                            WHERE profile_id = %s
                              AND video_id IS NOT NULL
                        ),
                        0,
                        0,
                        %s,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    RETURNING embedding_job_id
                    """,
                    (profile_id, profile_id, batch_size),
                )

                row = cursor.fetchone()
                return str(row[0])
    finally:
        connection.close()


def mark_job_running(embedding_job_id: str) -> None:
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE embedding_jobs
                    SET status = 'RUNNING',
                        started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
                        updated_at = CURRENT_TIMESTAMP,
                        error_message = NULL
                    WHERE embedding_job_id = %s
                    """,
                    (embedding_job_id,),
                )
    finally:
        connection.close()


def mark_job_completed(embedding_job_id: str) -> None:
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE embedding_jobs
                    SET status = 'COMPLETED',
                        completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE embedding_job_id = %s
                    """,
                    (embedding_job_id,),
                )
    finally:
        connection.close()


def mark_job_failed(embedding_job_id: str, error_message: str) -> None:
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE embedding_jobs
                    SET status = 'FAILED',
                        error_message = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE embedding_job_id = %s
                    """,
                    (error_message[:2000], embedding_job_id),
                )
    finally:
        connection.close()


def update_job_progress(embedding_job_id: str) -> None:
    """
    Progress is based on actual video_embeddings rows, not only status rows.
    This means old/pre-existing embeddings are counted correctly too.
    """
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE embedding_jobs j
                    SET embedded_videos = (
                            SELECT COUNT(DISTINCT r.video_id)
                            FROM raw_watch_events r
                            JOIN video_embeddings e
                              ON e.video_id = r.video_id
                            WHERE r.profile_id = j.profile_id
                              AND r.video_id IS NOT NULL
                        ),
                        failed_videos = (
                            SELECT COUNT(*)
                            FROM profile_video_embedding_status s
                            WHERE s.profile_id = j.profile_id
                              AND s.status = 'FAILED'
                        ),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE j.embedding_job_id = %s
                    """,
                    (embedding_job_id,),
                )
    finally:
        connection.close()


def get_progress_snapshot(embedding_job_id: str) -> dict:
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        embedding_job_id,
                        profile_id,
                        status,
                        total_videos,
                        embedded_videos,
                        failed_videos,
                        CASE
                            WHEN total_videos = 0 THEN 0
                            ELSE ROUND(
                                (embedded_videos::numeric / total_videos::numeric) * 100,
                                2
                            )
                        END AS progress_percent
                    FROM embedding_jobs
                    WHERE embedding_job_id = %s
                    """,
                    (embedding_job_id,),
                )

                row = cursor.fetchone()

                if not row:
                    return {}

                return {
                    "embedding_job_id": str(row[0]),
                    "profile_id": row[1],
                    "status": row[2],
                    "total_videos": row[3],
                    "embedded_videos": row[4],
                    "failed_videos": row[5],
                    "progress_percent": float(row[6]),
                }
    finally:
        connection.close()


def fetch_next_batch(
    profile_id: str,
    batch_size: int,
    model_name: str,
) -> list[dict]:
    """
    Fetch only videos for this profile that do not have embeddings for this model.

    Since video_embeddings has video_id as PRIMARY KEY, if a video exists with
    another model, this query treats it as missing for the current model and the
    save step will update it.
    """
    query = """
        SELECT DISTINCT
            y.video_id,
            y.title,
            y.description,
            y.tags,
            y.topic_categories
        FROM raw_watch_events r
        JOIN youtube_videos y
          ON y.video_id = r.video_id
        LEFT JOIN video_embeddings e
          ON e.video_id = y.video_id
         AND e.model_name = %s
        LEFT JOIN profile_video_embedding_status s
          ON s.profile_id = r.profile_id
         AND s.video_id = y.video_id
        WHERE r.profile_id = %s
          AND r.video_id IS NOT NULL
          AND e.video_id IS NULL
          AND (
                s.status IS NULL
                OR s.status = 'PENDING'
                OR s.status = 'FAILED'
                OR (
                    s.status = 'PROCESSING'
                    AND s.updated_at < CURRENT_TIMESTAMP - INTERVAL '30 minutes'
                )
          )
        ORDER BY y.video_id
        LIMIT %s
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (model_name, profile_id, batch_size))
                rows = cursor.fetchall()

                return [
                    {
                        "video_id": row[0],
                        "title": row[1],
                        "description": row[2],
                        "tags": row[3],
                        "topic_categories": row[4],
                    }
                    for row in rows
                ]
    finally:
        connection.close()


def mark_batch_processing(profile_id: str, videos: list[dict]) -> None:
    if not videos:
        return

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                for video in videos:
                    cursor.execute(
                        """
                        INSERT INTO profile_video_embedding_status (
                            profile_id,
                            video_id,
                            status,
                            error_message,
                            updated_at
                        )
                        VALUES (%s, %s, 'PROCESSING', NULL, CURRENT_TIMESTAMP)
                        ON CONFLICT (profile_id, video_id)
                        DO UPDATE SET
                            status = 'PROCESSING',
                            error_message = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (profile_id, video["video_id"]),
                    )
    finally:
        connection.close()


def save_embeddings(
    profile_id: str,
    videos: list[dict],
    embeddings,
    model_name: str,
) -> int:
    """
    Saves to your existing schema:

    video_embeddings(
        video_id TEXT PRIMARY KEY,
        embedding DOUBLE PRECISION[] NOT NULL,
        model_name TEXT NOT NULL,
        created_at TIMESTAMP
    )
    """
    saved = 0
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                for video, embedding in zip(videos, embeddings):
                    vector = [float(x) for x in embedding]

                    cursor.execute(
                        """
                        INSERT INTO video_embeddings (
                            video_id,
                            embedding,
                            model_name,
                            created_at
                        )
                        VALUES (%s, %s::double precision[], %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (video_id)
                        DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            model_name = EXCLUDED.model_name,
                            created_at = CURRENT_TIMESTAMP
                        """,
                        (
                            video["video_id"],
                            vector,
                            model_name,
                        ),
                    )

                    cursor.execute(
                        """
                        INSERT INTO profile_video_embedding_status (
                            profile_id,
                            video_id,
                            status,
                            error_message,
                            updated_at
                        )
                        VALUES (%s, %s, 'COMPLETED', NULL, CURRENT_TIMESTAMP)
                        ON CONFLICT (profile_id, video_id)
                        DO UPDATE SET
                            status = 'COMPLETED',
                            error_message = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (profile_id, video["video_id"]),
                    )

                    saved += 1

        return saved
    finally:
        connection.close()


def mark_batch_failed(
    profile_id: str,
    videos: list[dict],
    error_message: str,
) -> None:
    if not videos:
        return

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                for video in videos:
                    cursor.execute(
                        """
                        INSERT INTO profile_video_embedding_status (
                            profile_id,
                            video_id,
                            status,
                            error_message,
                            updated_at
                        )
                        VALUES (%s, %s, 'FAILED', %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (profile_id, video_id)
                        DO UPDATE SET
                            status = 'FAILED',
                            error_message = EXCLUDED.error_message,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (
                            profile_id,
                            video["video_id"],
                            error_message[:2000],
                        ),
                    )
    finally:
        connection.close()


def run_worker(
    profile_id: str,
    embedding_job_id: Optional[str],
    batch_size: int,
    max_batches: Optional[int],
    sleep_seconds: float,
    model_name: str,
) -> None:
    embedding_job_id = ensure_embedding_job(
        profile_id=profile_id,
        embedding_job_id=embedding_job_id,
        batch_size=batch_size,
    )

    print(f"[embedding-worker] profile_id={profile_id}")
    print(f"[embedding-worker] embedding_job_id={embedding_job_id}")
    print(f"[embedding-worker] model={model_name}")
    print(f"[embedding-worker] batch_size={batch_size}")

    mark_job_running(embedding_job_id)
    update_job_progress(embedding_job_id)

    print("[embedding-worker] loading model...")
    model = SentenceTransformer(model_name)
    print("[embedding-worker] model loaded")

    processed_batches = 0

    try:
        while True:
            if max_batches is not None and processed_batches >= max_batches:
                print("[embedding-worker] max_batches reached. Leaving job as RUNNING.")
                update_job_progress(embedding_job_id)
                break

            videos = fetch_next_batch(
                profile_id=profile_id,
                batch_size=batch_size,
                model_name=model_name,
            )

            if not videos:
                update_job_progress(embedding_job_id)
                mark_job_completed(embedding_job_id)

                snapshot = get_progress_snapshot(embedding_job_id)
                print(f"[embedding-worker] completed: {snapshot}")
                break

            mark_batch_processing(profile_id, videos)

            content_texts = [build_content_text(video) for video in videos]

            try:
                embeddings = model.encode(
                    content_texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    batch_size=batch_size,
                )

                saved = save_embeddings(
                    profile_id=profile_id,
                    videos=videos,
                    embeddings=embeddings,
                    model_name=model_name,
                )

                update_job_progress(embedding_job_id)

                processed_batches += 1
                snapshot = get_progress_snapshot(embedding_job_id)

                print(
                    "[embedding-worker] batch_complete "
                    f"batch={processed_batches} "
                    f"saved={saved} "
                    f"progress={snapshot.get('progress_percent')}% "
                    f"embedded={snapshot.get('embedded_videos')}/"
                    f"{snapshot.get('total_videos')}"
                )

            except Exception as batch_error:
                print(
                    f"[embedding-worker] batch_failed: {batch_error}",
                    file=sys.stderr,
                )

                mark_batch_failed(profile_id, videos, str(batch_error))
                update_job_progress(embedding_job_id)

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    except Exception as error:
        mark_job_failed(embedding_job_id, str(error))
        raise


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate video embeddings in resumable batches."
    )

    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--embedding-job-id", required=False)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-batches", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--model-name", default=MODEL_NAME)

    return parser.parse_args()


def main():
    args = parse_args()

    run_worker(
        profile_id=args.profile_id,
        embedding_job_id=args.embedding_job_id,
        batch_size=args.batch_size,
        max_batches=args.max_batches,
        sleep_seconds=args.sleep_seconds,
        model_name=args.model_name,
    )


if __name__ == "__main__":
    main()