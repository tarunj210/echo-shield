import argparse
import hashlib
from collections import defaultdict, Counter
from typing import Any

from datasets import load_dataset

from db import get_connection


MAX_TEXT_LENGTH = 2000


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_sample_id(source_dataset: str, split_name: str, text: str) -> str:
    digest = sha256_text(text)[:20]
    safe_source = source_dataset.replace("/", "_").replace(":", "_")
    return f"{safe_source}:{split_name}:{digest}"


def normalize_text(text: str | list[str] | None) -> str:
    if text is None:
        return ""

    if isinstance(text, list):
        text = " ".join(str(token) for token in text)

    text = str(text).replace("\n", " ").strip()

    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    return text


def insert_samples(samples: list[dict]) -> int:
    if not samples:
        return 0

    connection = get_connection()
    inserted = 0

    try:
        with connection:
            with connection.cursor() as cursor:
                for sample in samples:
                    cursor.execute(
                        """
                        INSERT INTO validation_samples (
                            sample_id,
                            source_dataset,
                            split_name,
                            source_label,
                            expected_category,
                            text,
                            text_sha256,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (sample_id)
                        DO UPDATE SET
                            source_dataset = EXCLUDED.source_dataset,
                            split_name = EXCLUDED.split_name,
                            source_label = EXCLUDED.source_label,
                            expected_category = EXCLUDED.expected_category,
                            text = EXCLUDED.text,
                            text_sha256 = EXCLUDED.text_sha256
                        """,
                        (
                            sample["sample_id"],
                            sample["source_dataset"],
                            sample["split_name"],
                            sample["source_label"],
                            sample["expected_category"],
                            sample["text"],
                            sample["text_sha256"],
                        ),
                    )
                    inserted += 1
    finally:
        connection.close()

    return inserted


def under_limit(counts: dict[str, int], category: str, max_per_category: int) -> bool:
    return counts[category] < max_per_category


def load_hf_dataset(name: str, config_name: str | None = None):
    """
    Loads only standard Hugging Face datasets.

    We intentionally do not use trust_remote_code because dataset loading scripts
    are no longer supported in recent versions of datasets and are not ideal for
    a portfolio-grade reproducible pipeline.
    """
    if config_name:
        return load_dataset(name, config_name)

    return load_dataset(name)


def get_first_existing(row: dict, candidate_keys: list[str]) -> Any:
    for key in candidate_keys:
        if key in row:
            return row[key]
    return None


def load_jigsaw(max_per_category: int) -> list[dict]:
    """
    Maps:
      identity_hate -> hate_or_extremism
      threat/insult/toxic/severe_toxic -> cyberbullying

    We avoid using 'obscene' alone as adult_content because profanity/obscenity is
    not the same thing as adult sexual content.
    """
    source_dataset = "thesofakillers/jigsaw-toxic-comment-classification-challenge"

    dataset = load_hf_dataset(source_dataset)
    split_name = "train"
    split = dataset[split_name]

    samples = []
    counts = defaultdict(int)

    for row in split:
        text = normalize_text(get_first_existing(row, ["comment_text", "text", "comment"]))

        if not text:
            continue

        toxic = int(row.get("toxic", 0) or 0)
        severe_toxic = int(row.get("severe_toxic", 0) or 0)
        threat = int(row.get("threat", 0) or 0)
        insult = int(row.get("insult", 0) or 0)
        identity_hate = int(row.get("identity_hate", 0) or 0)

        expected_category = None
        source_label = None

        if identity_hate == 1:
            expected_category = "hate_or_extremism"
            source_label = "identity_hate"
        elif threat == 1:
            expected_category = "cyberbullying"
            source_label = "threat"
        elif insult == 1:
            expected_category = "cyberbullying"
            source_label = "insult"
        elif severe_toxic == 1:
            expected_category = "cyberbullying"
            source_label = "severe_toxic"
        elif toxic == 1:
            expected_category = "cyberbullying"
            source_label = "toxic"
        else:
            expected_category = "low_or_unknown"
            source_label = "normal"

        if not under_limit(counts, expected_category, max_per_category):
            continue

        counts[expected_category] += 1

        samples.append({
            "sample_id": make_sample_id(source_dataset, split_name, text),
            "source_dataset": source_dataset,
            "split_name": split_name,
            "source_label": source_label,
            "expected_category": expected_category,
            "text": text,
            "text_sha256": sha256_text(text),
        })

    print(f"Jigsaw loaded counts: {dict(counts)}")
    return samples


def majority_label(labels: list[str]) -> str | None:
    if not labels:
        return None

    return Counter(labels).most_common(1)[0][0]


def load_hatexplain(max_per_category: int) -> list[dict]:
    """
    Maps:
      hatespeech -> hate_or_extremism
      offensive -> cyberbullying
      normal -> low_or_unknown
    """
    source_dataset = "Hate-speech-CNERG/hatexplain"

    dataset = load_hf_dataset(source_dataset)
    split_name = "train"
    split = dataset[split_name]

    samples = []
    counts = defaultdict(int)

    for row in split:
        text = normalize_text(get_first_existing(row, ["post_tokens", "text", "comment", "post"]))

        if not text:
            continue

        labels = []

        annotators = row.get("annotators")

        if isinstance(annotators, dict):
            label_values = annotators.get("label", [])
            labels = [str(label).lower() for label in label_values]
        else:
            label_value = row.get("label")
            if label_value is not None:
                labels = [str(label_value).lower()]

        label = majority_label(labels)

        if label is None:
            continue

        label = label.replace(" ", "").replace("_", "")

        if label in {"hatespeech", "hate"}:
            expected_category = "hate_or_extremism"
            source_label = "hatespeech"
        elif label in {"offensive", "offensivespeech"}:
            expected_category = "cyberbullying"
            source_label = "offensive"
        elif label in {"normal", "none"}:
            expected_category = "low_or_unknown"
            source_label = "normal"
        else:
            continue

        if not under_limit(counts, expected_category, max_per_category):
            continue

        counts[expected_category] += 1

        samples.append({
            "sample_id": make_sample_id(source_dataset, split_name, text),
            "source_dataset": source_dataset,
            "split_name": split_name,
            "source_label": source_label,
            "expected_category": expected_category,
            "text": text,
            "text_sha256": sha256_text(text),
        })

    print(f"HateXplain loaded counts: {dict(counts)}")
    return samples


def load_cyberbullying(max_per_category: int) -> list[dict]:
    """
    Maps:
      not_cyberbullying -> low_or_unknown
      religion/gender/ethnicity -> hate_or_extremism
      age/other_cyberbullying -> cyberbullying
    """
    source_dataset = "AnikaBasu/CyberbullyingDataset"

    dataset = load_hf_dataset(source_dataset)
    split_name = "train"
    split = dataset[split_name]

    samples = []
    counts = defaultdict(int)

    for row in split:
        text = normalize_text(get_first_existing(
            row,
            ["tweet_text", "text", "content", "sentence", "tweet"]
        ))

        if not text:
            continue

        label_raw = get_first_existing(
            row,
            ["cyberbullying_type", "label", "class", "target"]
        )

        if label_raw is None:
            continue

        label = str(label_raw).lower().strip()

        if label == "not_cyberbullying":
            expected_category = "low_or_unknown"
            source_label = label
        elif label in {"religion", "gender", "ethnicity", "race"}:
            expected_category = "hate_or_extremism"
            source_label = label
        elif label in {"age", "other_cyberbullying", "other"}:
            expected_category = "cyberbullying"
            source_label = label
        else:
            continue

        if not under_limit(counts, expected_category, max_per_category):
            continue

        counts[expected_category] += 1

        samples.append({
            "sample_id": make_sample_id(source_dataset, split_name, text),
            "source_dataset": source_dataset,
            "split_name": split_name,
            "source_label": source_label,
            "expected_category": expected_category,
            "text": text,
            "text_sha256": sha256_text(text),
        })

    print(f"Cyberbullying loaded counts: {dict(counts)}")
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=300,
        help="Maximum samples to load per mapped expected category per dataset.",
    )
    parser.add_argument(
    "--sources",
    nargs="+",
    default=["jigsaw", "cyberbullying"],
    choices=["jigsaw", "cyberbullying"],
    )

    args = parser.parse_args()

    all_samples = []

    if "jigsaw" in args.sources:
        all_samples.extend(load_jigsaw(args.max_per_category))

    

    if "cyberbullying" in args.sources:
        all_samples.extend(load_cyberbullying(args.max_per_category))

    inserted = insert_samples(all_samples)

    print(f"Total validation samples inserted/updated: {inserted}")

    summary = Counter(sample["expected_category"] for sample in all_samples)
    print(f"Expected category summary: {dict(summary)}")


if __name__ == "__main__":
    main()