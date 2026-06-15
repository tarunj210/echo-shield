import argparse
import re
from pathlib import Path

import numpy as np
import yaml
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from db import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
LABEL_SOURCE = "dynamic_keybert_topic_label_v1"

BLOCKED_TERMS = {
    "youtube", "shorts", "short", "video", "videos", "official", "channel",
    "subscribe", "follow", "viral", "trending", "status", "new", "full",
    "latest", "best", "clip", "clips", "watch", "like", "comment",
    "instagram", "twitter", "facebook", "tiktok", "reels"
}


def load_topic_taxonomy(path: str = "../config/topic_taxonomy.yml") -> list[dict]:
    taxonomy_path = Path(path)

    if not taxonomy_path.exists():
        raise FileNotFoundError(f"Topic taxonomy file not found: {taxonomy_path}")

    with taxonomy_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    categories = data.get("categories", [])

    if not categories:
        raise ValueError("No topic taxonomy categories found.")

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


def get_cluster_samples(cluster_id: str, limit: int = 80) -> list[dict]:
    query = """
        SELECT
            COALESCE(y.title, '') AS title,
            COALESCE(y.channel_title, '') AS channel_title,
            COALESCE(y.tags, '') AS tags
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

                return [
                    {
                        "title": row[0],
                        "channel_title": row[1],
                        "tags": row[2],
                    }
                    for row in cursor.fetchall()
                ]
    finally:
        connection.close()


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.replace("|", " ")
    value = re.sub(r"http\S+", " ", value)
    value = re.sub(r"[@#]\w+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def build_cluster_document(cluster: dict, samples: list[dict]) -> str:
    parts = [
        clean_text(cluster.get("cluster_label")),
        clean_text(cluster.get("summary")),
        clean_text(cluster.get("top_terms")),
        clean_text(cluster.get("keybert_keywords")),
    ]

    for sample in samples:
        title = clean_text(sample.get("title"))
        channel = clean_text(sample.get("channel_title"))
        tags = clean_text(sample.get("tags"))

        if title:
            # Titles are strongest, so include twice.
            parts.append(title)
            parts.append(title)

        if channel:
            parts.append(channel)

        if tags:
            parts.append(tags)

    return " ".join(part for part in parts if part).strip()


def clean_phrase(phrase: str) -> str | None:
    phrase = phrase.lower()
    phrase = re.sub(r"[^a-zA-Z0-9\s&]", " ", phrase)
    phrase = re.sub(r"\s+", " ", phrase).strip()

    if not phrase:
        return None

    words = []

    for word in phrase.split():
        if word in BLOCKED_TERMS:
            continue

        if len(word) <= 2 and not word.isdigit():
            continue

        if len(word) > 18:
            continue

        words.append(word)

    if not words:
        return None

    words = words[:6]

    return " ".join(word.capitalize() for word in words)


def extract_dynamic_keyphrases(
    kw_model: KeyBERT,
    cluster_document: str,
    top_n: int = 12,
) -> list[str]:
    if not cluster_document.strip():
        return []

    keywords = kw_model.extract_keywords(
        cluster_document,
        keyphrase_ngram_range=(1, 4),
        stop_words="english",
        top_n=top_n,
        use_mmr=True,
        diversity=0.65,
    )

    phrases = []

    for phrase, _score in keywords:
        cleaned = clean_phrase(phrase)

        if cleaned and cleaned not in phrases:
            phrases.append(cleaned)

    return phrases


def map_parent_label(
    cluster_embedding: np.ndarray,
    taxonomy_embeddings: np.ndarray,
    taxonomy: list[dict],
    threshold: float,
    min_margin: float,
) -> dict:
    similarities = cosine_similarity(
        cluster_embedding.reshape(1, -1),
        taxonomy_embeddings,
    )[0]

    ranked = np.argsort(similarities)[::-1]

    best_index = int(ranked[0])
    second_index = int(ranked[1]) if len(ranked) > 1 else best_index

    best_score = float(similarities[best_index])
    second_score = float(similarities[second_index])
    margin = best_score - second_score

    if best_score < threshold:
        return {
            "parent_label": "General / Mixed",
            "confidence": round(best_score, 3),
            "margin": round(margin, 3),
            "reason": "below_threshold",
        }

    if margin < min_margin:
        return {
            "parent_label": "General / Mixed",
            "confidence": round(best_score, 3),
            "margin": round(margin, 3),
            "reason": "ambiguous",
        }

    return {
        "parent_label": taxonomy[best_index]["parent_label"],
        "confidence": round(best_score, 3),
        "margin": round(margin, 3),
        "reason": "assigned",
    }


def score_display_phrase(
    phrase: str,
    phrase_embedding: np.ndarray,
    cluster_embedding: np.ndarray,
    parent_embedding: np.ndarray,
) -> float:
    phrase_cluster_similarity = cosine_similarity(
        phrase_embedding.reshape(1, -1),
        cluster_embedding.reshape(1, -1),
    )[0][0]

    phrase_parent_similarity = cosine_similarity(
        phrase_embedding.reshape(1, -1),
        parent_embedding.reshape(1, -1),
    )[0][0]

    word_count = len(phrase.split())

    if 2 <= word_count <= 5:
        length_bonus = 0.08
    elif word_count == 1:
        length_bonus = -0.05
    else:
        length_bonus = 0.0

    return (
        0.75 * float(phrase_cluster_similarity)
        + 0.20 * float(phrase_parent_similarity)
        + length_bonus
    )


def choose_dynamic_display_label(
    phrases: list[str],
    parent_label: str,
    cluster_embedding: np.ndarray,
    parent_embedding: np.ndarray,
    model: SentenceTransformer,
) -> tuple[str, str]:
    if not phrases:
        return parent_label, "fallback_parent_label"

    phrase_embeddings = model.encode(
        phrases,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    scored = []

    for phrase, embedding in zip(phrases, phrase_embeddings):
        score = score_display_phrase(
            phrase=phrase,
            phrase_embedding=embedding,
            cluster_embedding=cluster_embedding,
            parent_embedding=parent_embedding,
        )

        scored.append((phrase, score))

    scored = sorted(scored, key=lambda item: item[1], reverse=True)

    best_phrase = scored[0][0]

    # If the best phrase is too vague, use parent label.
    if len(best_phrase.split()) == 1 and parent_label != "General / Mixed":
        return parent_label, "fallback_parent_due_to_short_phrase"

    return best_phrase, "dynamic_keyphrase_ranked"


def save_refined_labels(rows: list[dict]) -> int:
    connection = get_connection()
    saved = 0

    try:
        with connection:
            with connection.cursor() as cursor:
                for row in rows:
                    cursor.execute(
                        """
                        UPDATE content_clusters
                        SET
                            raw_cluster_label = COALESCE(raw_cluster_label, cluster_label),
                            display_label = %s,
                            parent_label = %s,
                            parent_label_confidence = %s,
                            parent_label_margin = %s,
                            label_refinement_reason = %s,
                            label_source = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE cluster_id = %s
                        """,
                        (
                            row["display_label"],
                            row["parent_label"],
                            row["confidence"],
                            row["margin"],
                            row["reason"],
                            LABEL_SOURCE,
                            row["cluster_id"],
                        ),
                    )

                    saved += 1
    finally:
        connection.close()

    return saved


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--taxonomy",
        default="../config/topic_taxonomy.yml",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.17,
    )

    parser.add_argument(
        "--min-margin",
        type=float,
        default=0.02,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    print("Loading topic taxonomy...")
    taxonomy = load_topic_taxonomy(args.taxonomy)

    print("Loading clusters...")
    clusters = get_clusters(limit=args.limit)
    print(f"Loaded clusters: {len(clusters)}")

    if not clusters:
        print("No clusters found.")
        return

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)
    kw_model = KeyBERT(model=model)

    taxonomy_texts = [
        f"{item['parent_label']} {item['description']}"
        for item in taxonomy
    ]

    print("Embedding topic taxonomy...")
    taxonomy_embeddings = model.encode(
        taxonomy_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    refined_rows = []

    for index, cluster in enumerate(clusters, start=1):
        cluster_id = cluster["cluster_id"]

        samples = get_cluster_samples(cluster_id, limit=80)
        cluster_document = build_cluster_document(cluster, samples)

        if not cluster_document:
            refined_rows.append({
                "cluster_id": cluster_id,
                "display_label": "General / Mixed",
                "parent_label": "General / Mixed",
                "confidence": 0.0,
                "margin": 0.0,
                "reason": "empty_cluster_document",
            })
            continue

        cluster_embedding = model.encode(
            cluster_document,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        parent_mapping = map_parent_label(
            cluster_embedding=cluster_embedding,
            taxonomy_embeddings=taxonomy_embeddings,
            taxonomy=taxonomy,
            threshold=args.threshold,
            min_margin=args.min_margin,
        )

        parent_label = parent_mapping["parent_label"]

        parent_index = next(
            (
                i for i, item in enumerate(taxonomy)
                if item["parent_label"] == parent_label
            ),
            None,
        )

        if parent_index is None:
            parent_embedding = cluster_embedding
        else:
            parent_embedding = taxonomy_embeddings[parent_index]

        phrases = extract_dynamic_keyphrases(
            kw_model=kw_model,
            cluster_document=cluster_document,
            top_n=12,
        )

        display_label, display_reason = choose_dynamic_display_label(
            phrases=phrases,
            parent_label=parent_label,
            cluster_embedding=cluster_embedding,
            parent_embedding=parent_embedding,
            model=model,
        )

        reason = f"{parent_mapping['reason']}|{display_reason}"

        refined_rows.append({
            "cluster_id": cluster_id,
            "display_label": display_label,
            "parent_label": parent_label,
            "confidence": parent_mapping["confidence"],
            "margin": parent_mapping["margin"],
            "reason": reason,
        })

        print(
            f"{index}/{len(clusters)} {cluster_id}: "
            f"{display_label} → {parent_label} "
            f"(confidence={parent_mapping['confidence']}, margin={parent_mapping['margin']})"
        )

    saved = save_refined_labels(refined_rows)

    print(f"Saved refined labels: {saved}")


if __name__ == "__main__":
    main()