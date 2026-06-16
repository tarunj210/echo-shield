import argparse
from pathlib import Path
from collections import Counter

import numpy as np
import yaml
from sentence_transformers import SentenceTransformer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.metrics.pairwise import cosine_similarity

from db import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_VERSION = "public_dataset_taxonomy_validation_v1"
DEFAULT_TAXONOMY_THRESHOLD = 0.14


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


def get_validation_samples(limit: int | None = None) -> list[dict]:
    query = """
        SELECT
            sample_id,
            text,
            expected_category,
            source_dataset,
            source_label
        FROM validation_samples
        ORDER BY source_dataset, expected_category, sample_id
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
                        "sample_id": row[0],
                        "text": row[1],
                        "expected_category": row[2],
                        "source_dataset": row[3],
                        "source_label": row[4],
                    }
                    for row in rows
                ]
    finally:
        connection.close()


def map_text_to_taxonomy(
    text_embedding: np.ndarray,
    taxonomy_embeddings: np.ndarray,
    taxonomy: list[dict],
    threshold: float,
) -> dict:
    similarities = cosine_similarity(
        text_embedding.reshape(1, -1),
        taxonomy_embeddings,
    )[0]

    best_index = int(np.argmax(similarities))
    best_score = float(similarities[best_index])
    best_category = taxonomy[best_index]

    category_name = best_category["category"]

    if best_score < threshold:
        return {
            "predicted_category": "low_or_unknown",
            "predicted_topic": "General or unknown content",
            "confidence": round(best_score, 3),
            "risk_score": 0.10,
        }

    base_risk = float(best_category.get("base_risk", 0.5))
    risk_score = base_risk * min(1.0, best_score / 0.60)
    risk_score = max(0.10, min(risk_score, 0.95))

    return {
        "predicted_category": category_name,
        "predicted_topic": best_category["topic"],
        "confidence": round(best_score, 3),
        "risk_score": round(risk_score, 3),
    }


def save_predictions(samples: list[dict], predictions: list[dict]) -> int:
    connection = get_connection()
    saved = 0

    try:
        with connection:
            with connection.cursor() as cursor:
                for sample, prediction in zip(samples, predictions):
                    is_match = sample["expected_category"] == prediction["predicted_category"]

                    cursor.execute(
                        """
                        INSERT INTO validation_predictions (
                            sample_id,
                            expected_category,
                            predicted_category,
                            predicted_topic,
                            confidence,
                            risk_score,
                            is_match,
                            model_version,
                            evaluated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (sample_id)
                        DO UPDATE SET
                            expected_category = EXCLUDED.expected_category,
                            predicted_category = EXCLUDED.predicted_category,
                            predicted_topic = EXCLUDED.predicted_topic,
                            confidence = EXCLUDED.confidence,
                            risk_score = EXCLUDED.risk_score,
                            is_match = EXCLUDED.is_match,
                            model_version = EXCLUDED.model_version,
                            evaluated_at = CURRENT_TIMESTAMP
                        """,
                        (
                            sample["sample_id"],
                            sample["expected_category"],
                            prediction["predicted_category"],
                            prediction["predicted_topic"],
                            prediction["confidence"],
                            prediction["risk_score"],
                            is_match,
                            MODEL_VERSION,
                        ),
                    )
                    saved += 1
    finally:
        connection.close()

    return saved


def print_binary_risk_report(y_true: list[str], y_pred: list[str]):
    def to_binary(category: str) -> str:
        return "low_or_unknown" if category == "low_or_unknown" else "risk_relevant"

    y_true_binary = [to_binary(category) for category in y_true]
    y_pred_binary = [to_binary(category) for category in y_pred]

    print("\nBinary risk-vs-low report:")
    print(classification_report(
        y_true_binary,
        y_pred_binary,
        digits=3,
        zero_division=0,
    ))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of validation samples to evaluate.",
    )

    parser.add_argument(
        "--taxonomy",
        default="../config/safety_taxonomy.yml",
        help="Path to safety taxonomy YAML file.",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_TAXONOMY_THRESHOLD,
        help="Similarity threshold for assigning a risk category.",
    )

    parser.add_argument(
        "--candidate-categories",
        nargs="+",
        default=None,
        help="Restrict taxonomy candidates for this validation run.",
    )

    args = parser.parse_args()

    print("Loading taxonomy...")
    taxonomy = load_taxonomy(args.taxonomy)

    print(f"Taxonomy categories: {[category['category'] for category in taxonomy]}")

    print("Loading validation samples...")
    samples = get_validation_samples(limit=args.limit)

    print(f"Validation samples: {len(samples)}")

    if not samples:
        print("No validation samples found. Run load_public_validation_samples.py first.")
        return

    expected_risk_categories = sorted({
        sample["expected_category"]
        for sample in samples
        if sample["expected_category"] != "low_or_unknown"
    })

    candidate_categories = args.candidate_categories or expected_risk_categories
    candidate_category_set = set(candidate_categories)

    risk_taxonomy = [
        category
        for category in taxonomy
        if category["category"] in candidate_category_set
    ]

    if not risk_taxonomy:
        raise ValueError(
            f"No matching taxonomy categories found for candidates: {candidate_categories}"
        )

    print(f"Validation candidate categories: {candidate_categories}")
    print(f"Threshold: {args.threshold}")

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    taxonomy_texts = [
        f"{category['category']} {category['topic']} {category['description']}"
        for category in risk_taxonomy
    ]

    print("Embedding taxonomy...")
    taxonomy_embeddings = model.encode(
        taxonomy_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    sample_texts = [sample["text"] for sample in samples]

    print("Embedding validation samples...")
    sample_embeddings = model.encode(
        sample_texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=32,
    )

    print("Predicting taxonomy labels...")
    predictions = [
        map_text_to_taxonomy(
            text_embedding=embedding,
            taxonomy_embeddings=taxonomy_embeddings,
            taxonomy=risk_taxonomy,
            threshold=args.threshold,
        )
        for embedding in sample_embeddings
    ]

    saved = save_predictions(samples, predictions)

    print(f"Saved predictions: {saved}")

    y_true = [sample["expected_category"] for sample in samples]
    y_pred = [prediction["predicted_category"] for prediction in predictions]

    print("\nExpected distribution:")
    print(dict(Counter(y_true)))

    print("\nPredicted distribution:")
    print(dict(Counter(y_pred)))

    print("\nCategory-level report:")
    report_labels = sorted(set(candidate_categories) | {"low_or_unknown"})

    print(classification_report(
        y_true,
        y_pred,
        labels=report_labels,
        digits=3,
        zero_division=0,
    ))

    labels = sorted(set(y_true) | set(y_pred))

    print("\nLabels:")
    print(labels)

    print("\nConfusion matrix:")
    print(confusion_matrix(y_true, y_pred, labels=labels))

    print_binary_risk_report(y_true, y_pred)


if __name__ == "__main__":
    main()