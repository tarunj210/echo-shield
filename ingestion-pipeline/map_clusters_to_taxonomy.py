import sys
from pathlib import Path

import numpy as np
import yaml
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from db import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_VERSION = "cluster_taxonomy_mapping_v1"
TAXONOMY_THRESHOLD = 0.34


def load_taxonomy(path: str = "../config/safety_taxonomy.yml") -> list[dict]:
    taxonomy_path = Path(path)

    if not taxonomy_path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {taxonomy_path}")

    with taxonomy_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    categories = data.get("categories", [])

    if not categories:
        raise ValueError("No categories found in safety taxonomy config.")

    return categories


def get_clusters(limit: int | None = None) -> list[dict]:
    query = """
        SELECT
            cluster_id,
            cluster_label,
            summary,
            top_terms,
            keybert_keywords,
            video_count
        FROM content_clusters
        ORDER BY video_count DESC
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
                        "cluster_id": row[0],
                        "cluster_label": row[1],
                        "summary": row[2],
                        "top_terms": row[3],
                        "keybert_keywords": row[4],
                        "video_count": row[5],
                    }
                    for row in rows
                ]
    finally:
        connection.close()


def get_cluster_sample_titles(cluster_id: str, limit: int = 25) -> list[str]:
    query = """
        SELECT y.title
        FROM video_cluster_assignments a
        JOIN youtube_videos y
            ON a.video_id = y.video_id
        WHERE a.cluster_id = %s
        LIMIT %s
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (cluster_id, limit))
                return [row[0] for row in cursor.fetchall() if row[0]]
    finally:
        connection.close()


def build_cluster_text(cluster: dict, sample_titles: list[str]) -> str:
    return " ".join([
        cluster.get("cluster_label") or "",
        cluster.get("summary") or "",
        (cluster.get("top_terms") or "").replace("|", " "),
        (cluster.get("keybert_keywords") or "").replace("|", " "),
        " ".join(sample_titles),
    ]).strip()


def map_cluster_to_taxonomy(
    cluster_embedding: np.ndarray,
    taxonomy_embeddings: np.ndarray,
    taxonomy: list[dict],
) -> dict:
    similarities = cosine_similarity(
        cluster_embedding.reshape(1, -1),
        taxonomy_embeddings,
    )[0]

    best_index = int(np.argmax(similarities))
    best_score = float(similarities[best_index])
    best_category = taxonomy[best_index]

    if best_score < TAXONOMY_THRESHOLD:
        return {
            "inferred_topic": "General or unknown content cluster",
            "inferred_risk_category": "low_or_unknown",
            "risk_score": 0.10,
            "confidence": round(best_score, 3),
            "explanation": (
                f"No safety taxonomy category exceeded threshold {TAXONOMY_THRESHOLD}. "
                f"Closest category was '{best_category['category']}' "
                f"with similarity {best_score:.3f}."
            ),
        }

    if best_category["category"] == "educational":
        return {
            "inferred_topic": best_category["topic"],
            "inferred_risk_category": "low_or_unknown",
            "risk_score": 0.05,
            "confidence": round(best_score, 3),
            "explanation": (
                f"Cluster was closest to educational taxonomy "
                f"with similarity {best_score:.3f}."
            ),
        }

    base_risk = float(best_category.get("base_risk", 0.5))

    # Risk is based on category severity and semantic match confidence.
    risk_score = base_risk * min(1.0, best_score / 0.60)
    risk_score = max(0.10, min(risk_score, 0.95))

    return {
        "inferred_topic": best_category["topic"],
        "inferred_risk_category": best_category["category"],
        "risk_score": round(risk_score, 3),
        "confidence": round(best_score, 3),
        "explanation": (
            f"Discovered semantic cluster was closest to taxonomy category "
            f"'{best_category['category']}' with cosine similarity {best_score:.3f}. "
            f"This taxonomy label is interpretive; it was not used to create the cluster."
        ),
    }


def save_labels(labels: list[tuple[str, dict]]) -> int:
    connection = get_connection()
    saved = 0

    try:
        with connection:
            with connection.cursor() as cursor:
                for cluster_id, label in labels:
                    cursor.execute(
                        """
                        INSERT INTO cluster_taxonomy_labels (
                            cluster_id,
                            inferred_topic,
                            inferred_risk_category,
                            risk_score,
                            confidence,
                            explanation,
                            model_version,
                            labelled_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (cluster_id)
                        DO UPDATE SET
                            inferred_topic = EXCLUDED.inferred_topic,
                            inferred_risk_category = EXCLUDED.inferred_risk_category,
                            risk_score = EXCLUDED.risk_score,
                            confidence = EXCLUDED.confidence,
                            explanation = EXCLUDED.explanation,
                            model_version = EXCLUDED.model_version,
                            labelled_at = CURRENT_TIMESTAMP
                        """,
                        (
                            cluster_id,
                            label["inferred_topic"],
                            label["inferred_risk_category"],
                            label["risk_score"],
                            label["confidence"],
                            label["explanation"],
                            MODEL_VERSION,
                        ),
                    )
                    saved += 1
    finally:
        connection.close()

    return saved


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    print("Loading taxonomy...")
    taxonomy = load_taxonomy()

    print(f"Loaded taxonomy categories: {len(taxonomy)}")

    print("Loading clusters...")
    clusters = get_clusters(limit=limit)

    print(f"Loaded clusters: {len(clusters)}")

    if not clusters:
        print("No clusters found. Run discover_semantic_clusters.py first.")
        return

    model = SentenceTransformer(MODEL_NAME)

    taxonomy_texts = [
        category["description"]
        for category in taxonomy
    ]

    print("Embedding taxonomy descriptions...")
    taxonomy_embeddings = model.encode(
        taxonomy_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    cluster_texts = []

    print("Building cluster texts...")
    for cluster in clusters:
        sample_titles = get_cluster_sample_titles(cluster["cluster_id"], limit=25)
        cluster_text = build_cluster_text(cluster, sample_titles)
        cluster_texts.append(cluster_text)

    print("Embedding clusters...")
    cluster_embeddings = model.encode(
        cluster_texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=16,
    )

    print("Mapping clusters to taxonomy...")
    labels = []

    for cluster, embedding in zip(clusters, cluster_embeddings):
        label = map_cluster_to_taxonomy(
            cluster_embedding=embedding,
            taxonomy_embeddings=taxonomy_embeddings,
            taxonomy=taxonomy,
        )
        labels.append((cluster["cluster_id"], label))

    saved = save_labels(labels)

    print(f"Saved taxonomy labels: {saved}")

    print("Mapped clusters:")
    for cluster, (_, label) in zip(clusters[:20], labels[:20]):
        print(
            f"{cluster['cluster_id']} | {cluster.get('cluster_label')} "
            f"→ {label['inferred_risk_category']} "
            f"(confidence={label['confidence']}, risk={label['risk_score']})"
        )


if __name__ == "__main__":
    main()