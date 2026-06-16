import sys
import numpy as np
from sklearn.neighbors import NearestNeighbors

from db import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_embeddings(limit: int | None = None) -> tuple[list[str], np.ndarray]:
    query = """
        SELECT video_id, embedding
        FROM video_embeddings
        ORDER BY video_id
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

                video_ids = [row[0] for row in rows]
                embeddings = np.array([row[1] for row in rows], dtype=np.float32)

                return video_ids, embeddings
    finally:
        connection.close()


def clear_existing_edges():
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM video_similarity_edges")
    finally:
        connection.close()


def save_similarity_edges(edges: list[tuple[str, str, float]]) -> int:
    if not edges:
        return 0

    connection = get_connection()
    saved = 0

    try:
        with connection:
            with connection.cursor() as cursor:
                for source_id, target_id, similarity in edges:
                    cursor.execute(
                        """
                        INSERT INTO video_similarity_edges (
                            source_video_id,
                            target_video_id,
                            similarity,
                            model_name,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (source_video_id, target_video_id)
                        DO UPDATE SET
                            similarity = EXCLUDED.similarity,
                            model_name = EXCLUDED.model_name,
                            created_at = CURRENT_TIMESTAMP
                        """,
                        (
                            source_id,
                            target_id,
                            similarity,
                            MODEL_NAME,
                        ),
                    )
                    saved += 1
    finally:
        connection.close()

    return saved


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    top_k = 25
    threshold = 0.60

    video_ids, embeddings = get_embeddings(limit=limit)

    print(f"Loaded embeddings: {len(video_ids)}")

    if len(video_ids) < 2:
        print("Need at least 2 videos to build similarity edges.")
        return

    print("Building nearest-neighbour index...")

    neighbours = NearestNeighbors(
        n_neighbors=min(top_k + 1, len(video_ids)),
        metric="cosine",
        algorithm="brute",
    )

    neighbours.fit(embeddings)

    print("Finding nearest neighbours...")
    distances, indices = neighbours.kneighbors(embeddings)

    edges = {}

    for source_idx, neighbour_indices in enumerate(indices):
        source_id = video_ids[source_idx]

        for distance, target_idx in zip(distances[source_idx], neighbour_indices):
            target_id = video_ids[target_idx]

            if source_id == target_id:
                continue

            similarity = 1.0 - float(distance)

            if similarity < threshold:
                continue

            left, right = sorted([source_id, target_id])
            key = (left, right)

            edges[key] = max(edges.get(key, 0), round(similarity, 4))

    deduped_edges = [
        (source_id, target_id, similarity)
        for (source_id, target_id), similarity in edges.items()
    ]

    print(f"Generated similarity edges: {len(deduped_edges)}")

    print("Clearing previous similarity edges...")
    clear_existing_edges()

    print("Saving similarity edges...")
    saved = save_similarity_edges(deduped_edges)

    print(f"Saved similarity edges: {saved}")


if __name__ == "__main__":
    main()