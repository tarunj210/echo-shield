from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

from db import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
LABELLING_METHOD = "keybert_v1"


def get_clusters(min_video_count: int = 5) -> list[dict]:
    query = """
        SELECT cluster_id, video_count
        FROM content_clusters
        WHERE video_count >= %s
        ORDER BY video_count DESC
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (min_video_count,))
                rows = cursor.fetchall()

                return [
                    {
                        "cluster_id": row[0],
                        "video_count": row[1],
                    }
                    for row in rows
                ]
    finally:
        connection.close()


def get_cluster_text(cluster_id: str, limit: int = 80) -> str:
    """
    Builds one text document for a discovered cluster.

    Titles and tags are more useful than full descriptions for YouTube metadata.
    Descriptions can be noisy, so we truncate them.
    """
    query = """
        SELECT
            COALESCE(y.title, '') AS title,
            COALESCE(y.description, '') AS description,
            COALESCE(y.tags, '') AS tags,
            COALESCE(y.channel_title, '') AS channel_title
        FROM video_cluster_assignments a
        JOIN youtube_videos y
            ON a.video_id = y.video_id
        WHERE a.cluster_id = %s
        LIMIT %s
    """

    connection = get_connection()
    parts = []

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (cluster_id, limit))

                for title, description, tags, channel_title in cursor.fetchall():
                    if title:
                        # Add title twice because it is usually the strongest signal.
                        parts.append(title)
                        parts.append(title)

                    if tags:
                        parts.append(tags.replace("|", " "))

                    if channel_title:
                        parts.append(channel_title)

                    if description:
                        parts.append(description[:500])

    finally:
        connection.close()

    return " ".join(parts)


def make_cluster_label(keywords: list[tuple[str, float]]) -> str:
    if not keywords:
        return "General content cluster"

    phrases = [phrase for phrase, _ in keywords[:4]]
    return ", ".join(phrases)


def save_cluster_label(
    cluster_id: str,
    cluster_label: str,
    keywords: list[tuple[str, float]],
):
    keyword_text = "|".join([
        f"{phrase}:{score:.4f}"
        for phrase, score in keywords
    ])

    summary = (
        f"Cluster labelled using KeyBERT. "
        f"Top keywords: {', '.join([phrase for phrase, _ in keywords[:8]])}."
    )

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE content_clusters
                    SET
                        cluster_label = %s,
                        summary = %s,
                        keybert_keywords = %s,
                        labelling_method = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE cluster_id = %s
                    """,
                    (
                        cluster_label,
                        summary,
                        keyword_text,
                        LABELLING_METHOD,
                        cluster_id,
                    ),
                )
    finally:
        connection.close()


def main():
    min_video_count = 5

    clusters = get_clusters(min_video_count=min_video_count)

    print(f"Loaded {len(clusters)} clusters with at least {min_video_count} videos")

    if not clusters:
        print("No clusters found. Run discover_semantic_clusters.py first.")
        return

    sentence_model = SentenceTransformer(MODEL_NAME)
    kw_model = KeyBERT(model=sentence_model)

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        video_count = cluster["video_count"]

        text = get_cluster_text(cluster_id)

        if not text.strip():
            print(f"{cluster_id}: no usable text")
            continue

        try:
            keywords = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),
                stop_words="english",
                top_n=10,
                use_mmr=True,
                diversity=0.6,
            )
        except ValueError as error:
            print(f"{cluster_id}: KeyBERT failed: {error}")
            continue

        cluster_label = make_cluster_label(keywords)

        save_cluster_label(cluster_id, cluster_label, keywords)

        print(f"{cluster_id} ({video_count} videos) -> {cluster_label}")


if __name__ == "__main__":
    main()