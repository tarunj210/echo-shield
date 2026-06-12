import re
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer

from db import get_connection


MODEL_VERSION = "semantic_louvain_v1"


def clean_text(value: str | None) -> str:
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


def get_all_embedded_video_ids() -> list[str]:
    query = """
        SELECT video_id
        FROM video_embeddings
        ORDER BY video_id
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def get_similarity_edges(min_similarity: float = 0.72) -> list[tuple[str, str, float]]:
    query = """
        SELECT source_video_id, target_video_id, similarity
        FROM video_similarity_edges
        WHERE similarity >= %s
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (min_similarity,))
                return [
                    (row[0], row[1], float(row[2]))
                    for row in cursor.fetchall()
                ]
    finally:
        connection.close()


def get_video_texts(video_ids: list[str]) -> dict[str, str]:
    if not video_ids:
        return {}

    query = """
        SELECT video_id, title, description, tags, topic_categories
        FROM youtube_videos
        WHERE video_id = ANY(%s)
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (video_ids,))
                rows = cursor.fetchall()

                lookup = {}

                for row in rows:
                    video = {
                        "title": row[1],
                        "description": row[2],
                        "tags": row[3],
                        "topic_categories": row[4],
                    }
                    lookup[row[0]] = build_content_text(video)

                return lookup
    finally:
        connection.close()


def build_graph(
    all_video_ids: list[str],
    edges: list[tuple[str, str, float]],
) -> nx.Graph:
    graph = nx.Graph()

    # Add only nodes that participate in similarity edges.
    # Isolated videos are not useful for semantic clustering.
    for source, target, similarity in edges:
        graph.add_edge(source, target, weight=similarity)

    return graph


def extract_top_terms(video_texts: list[str], top_n: int = 8) -> list[str]:
    docs = [text for text in video_texts if text and text.strip()]

    if not docs:
        return []

    # For tiny clusters, max_df=0.85 can remove every word.
    # So use max_df=1.0 when the cluster has only a few documents.
    max_df_value = 1.0 if len(docs) <= 2 else 0.95

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=3000,
            ngram_range=(1, 2),
            min_df=1,
            max_df=max_df_value,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]+\b",
        )

        matrix = vectorizer.fit_transform(docs)

        scores = matrix.sum(axis=0).A1
        terms = vectorizer.get_feature_names_out()

        ranked = sorted(
            zip(terms, scores),
            key=lambda item: item[1],
            reverse=True,
        )

        return [term for term, _ in ranked[:top_n]]

    except ValueError:
        # Fallback for clusters with very little/noisy text.
        combined = " ".join(docs).lower()
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]{2,}\b", combined)

        blocked = {
            "the", "and", "for", "you", "with", "this", "that",
            "from", "video", "youtube", "watch", "official",
            "shorts", "channel", "subscribe"
        }

        counts = {}

        for token in tokens:
            if token in blocked:
                continue

            counts[token] = counts.get(token, 0) + 1

        ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)

        return [term for term, _ in ranked[:top_n]]


def save_clusters(
    communities: list[set[str]],
    video_text_lookup: dict[str, str],
) -> int:
    connection = get_connection()
    saved_clusters = 0

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM video_cluster_assignments")
                cursor.execute("DELETE FROM content_clusters")

                for index, community in enumerate(communities, start=1):
                    cluster_id = f"cluster_{index:04d}"
                    video_ids = sorted(list(community))

                    video_texts = [
                        video_text_lookup.get(video_id, "")
                        for video_id in video_ids
                    ]

                    top_terms = extract_top_terms(video_texts, top_n=8)

                    if top_terms:
                        cluster_label = ", ".join(top_terms[:4])
                        summary = (
                            f"Semantic cluster with {len(video_ids)} videos. "
                            f"Top terms: {', '.join(top_terms)}."
                        )
                    else:
                        cluster_label = f"Cluster {index}"
                        summary = f"Semantic cluster with {len(video_ids)} videos."

                    cursor.execute(
                        """
                        INSERT INTO content_clusters (
                            cluster_id,
                            cluster_label,
                            summary,
                            top_terms,
                            video_count,
                            model_version,
                            created_at,
                            updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (
                            cluster_id,
                            cluster_label,
                            summary,
                            "|".join(top_terms),
                            len(video_ids),
                            MODEL_VERSION,
                        ),
                    )

                    for video_id in video_ids:
                        cursor.execute(
                            """
                            INSERT INTO video_cluster_assignments (
                                video_id,
                                cluster_id,
                                confidence,
                                assigned_at
                            )
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                            """,
                            (
                                video_id,
                                cluster_id,
                                1.0,
                            ),
                        )

                    saved_clusters += 1
    finally:
        connection.close()

    return saved_clusters


def main():
    min_similarity = 0.60
    resolution = 0.7

    print("Loading videos...")
    all_video_ids = get_all_embedded_video_ids()
    print(f"Embedded videos: {len(all_video_ids)}")

    if not all_video_ids:
        print("No embeddings found. Run generate_video_embeddings.py first.")
        return

    print("Loading similarity edges...")
    edges = get_similarity_edges(min_similarity=min_similarity)
    print(f"Similarity edges: {len(edges)}")

    if not edges:
        print("No similarity edges found. Run build_similarity_edges.py or lower similarity threshold.")
        return

    print("Building graph...")
    graph = build_graph(all_video_ids, edges)

    print(f"Graph nodes: {graph.number_of_nodes()}")
    print(f"Graph edges: {graph.number_of_edges()}")

    print("Running Louvain community detection...")
    communities = nx.community.louvain_communities(
        graph,
        weight="weight",
        resolution=resolution,
        seed=42,
    )

    min_cluster_size = 5

    communities = [
        community
        for community in communities
        if len(community) >= min_cluster_size
    ]

    communities = sorted(communities, key=len, reverse=True)

    print(f"Discovered clusters: {len(communities)}")

    print("Loading video text...")
    video_text_lookup = get_video_texts(all_video_ids)

    print("Saving clusters...")
    saved = save_clusters(communities, video_text_lookup)

    print(f"Saved clusters: {saved}")

    print("Top clusters:")
    for index, community in enumerate(communities[:10], start=1):
        print(f"  cluster_{index:04d}: {len(community)} videos")


if __name__ == "__main__":
    main()