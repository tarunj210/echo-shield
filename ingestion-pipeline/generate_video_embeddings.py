import sys
import re
from typing import Optional

from sentence_transformers import SentenceTransformer

from db import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""

    value = value.replace("|", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def build_content_text(row: dict) -> str:
    return " ".join([
        clean_text(row.get("title")),
        clean_text(row.get("description")),
        clean_text(row.get("tags")),
        clean_text(row.get("topic_categories")),
    ]).strip()


def get_videos_without_embeddings(limit: int | None = None) -> list[dict]:
    query = """
        SELECT
            y.video_id,
            y.title,
            y.description,
            y.tags,
            y.topic_categories
        FROM youtube_videos y
        LEFT JOIN video_embeddings e
            ON y.video_id = e.video_id
        WHERE e.video_id IS NULL
        ORDER BY y.collected_at DESC
    """

    params = ()

    if limit:
        query += " LIMIT %s"
        params = (limit,)

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
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


def save_embeddings(videos: list[dict], embeddings) -> int:
    connection = get_connection()
    saved = 0

    try:
        with connection:
            with connection.cursor() as cursor:
                for video, embedding in zip(videos, embeddings):
                    cursor.execute(
                        """
                        INSERT INTO video_embeddings (
                            video_id,
                            embedding,
                            model_name,
                            created_at
                        )
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (video_id)
                        DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            model_name = EXCLUDED.model_name,
                            created_at = CURRENT_TIMESTAMP
                        """,
                        (
                            video["video_id"],
                            embedding.astype(float).tolist(),
                            MODEL_NAME,
                        ),
                    )
                    saved += 1
    finally:
        connection.close()

    return saved


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    videos = get_videos_without_embeddings(limit=limit)

    print(f"Found {len(videos)} videos without embeddings")

    if not videos:
        print("No work to do.")
        return

    content_texts = [build_content_text(video) for video in videos]

    model = SentenceTransformer(MODEL_NAME)

    print("Generating embeddings...")
    embeddings = model.encode(
        content_texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=32,
    )

    saved = save_embeddings(videos, embeddings)

    print(f"Saved embeddings: {saved}")


if __name__ == "__main__":
    main()