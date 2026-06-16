import argparse
import math
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from db import get_connection


MODEL_VERSION = "temporal_drift_v1"


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def get_profiles() -> list[str]:
    query = """
        SELECT DISTINCT profile_id
        FROM raw_watch_events
        ORDER BY profile_id
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def get_latest_watch_time(profile_id: str) -> datetime | None:
    query = """
        SELECT MAX(watched_at)
        FROM raw_watch_events
        WHERE profile_id = %s
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (profile_id,))
                row = cursor.fetchone()
                return row[0] if row else None
    finally:
        connection.close()


def get_period_days(granularity: str) -> int:
    if granularity == "daily":
        return 1

    if granularity == "weekly":
        return 7

    if granularity == "monthly":
        return 30

    raise ValueError("granularity must be one of: daily, weekly, monthly")


def build_periods(anchor_time: datetime, granularity: str, periods: int) -> list[tuple[datetime, datetime]]:
    period_days = get_period_days(granularity)
    period_length = timedelta(days=period_days)

    end = anchor_time + timedelta(seconds=1)
    windows = []

    for _ in range(periods):
        start = end - period_length
        windows.append((start, end))
        end = start

    return list(reversed(windows))


def get_topic_counts(profile_id: str, window_start: datetime, window_end: datetime) -> tuple[dict[str, int], int]:
    query = """
        SELECT
            COALESCE(c.parent_label, 'General / Mixed') AS parent_label,
            COUNT(*) AS watch_count
        FROM raw_watch_events e
        JOIN video_cluster_assignments a
            ON e.video_id = a.video_id
        JOIN content_clusters c
            ON a.cluster_id = c.cluster_id
        WHERE e.profile_id = %s
          AND e.watched_at >= %s
          AND e.watched_at < %s
        GROUP BY COALESCE(c.parent_label, 'General / Mixed')
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (profile_id, window_start, window_end))
                rows = cursor.fetchall()

                counts = {row[0]: int(row[1]) for row in rows}
                total = sum(counts.values())

                return counts, total
    finally:
        connection.close()


def get_cluster_counts(profile_id: str, window_start: datetime, window_end: datetime) -> tuple[dict[str, int], int]:
    query = """
        SELECT
            a.cluster_id,
            COUNT(*) AS watch_count
        FROM raw_watch_events e
        JOIN video_cluster_assignments a
            ON e.video_id = a.video_id
        WHERE e.profile_id = %s
          AND e.watched_at >= %s
          AND e.watched_at < %s
        GROUP BY a.cluster_id
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (profile_id, window_start, window_end))
                rows = cursor.fetchall()

                counts = {row[0]: int(row[1]) for row in rows}
                total = sum(counts.values())

                return counts, total
    finally:
        connection.close()


def get_risk_exposure(profile_id: str, window_start: datetime, window_end: datetime) -> float:
    """
    Risk exposure is the average taxonomy risk score weighted by watch events.
    low_or_unknown contributes very little; higher-risk categories contribute more.
    """
    query = """
        SELECT
            COUNT(*) AS total_watches,
            SUM(COALESCE(t.risk_score, 0.10)) AS weighted_risk
        FROM raw_watch_events e
        JOIN video_cluster_assignments a
            ON e.video_id = a.video_id
        LEFT JOIN cluster_taxonomy_labels t
            ON a.cluster_id = t.cluster_id
        WHERE e.profile_id = %s
          AND e.watched_at >= %s
          AND e.watched_at < %s
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (profile_id, window_start, window_end))
                row = cursor.fetchone()

                total_watches = int(row[0] or 0)
                weighted_risk = float(row[1] or 0.0)

                if total_watches == 0:
                    return 0.0

                return weighted_risk / total_watches
    finally:
        connection.close()


def distribution_from_counts(
    previous_counts: dict[str, int],
    current_counts: dict[str, int],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    keys = sorted(set(previous_counts.keys()) | set(current_counts.keys()))

    previous_total = sum(previous_counts.values())
    current_total = sum(current_counts.values())

    if previous_total == 0:
        previous_total = 1

    if current_total == 0:
        current_total = 1

    previous_distribution = np.array(
        [previous_counts.get(key, 0) / previous_total for key in keys],
        dtype=float,
    )

    current_distribution = np.array(
        [current_counts.get(key, 0) / current_total for key in keys],
        dtype=float,
    )

    return previous_distribution, current_distribution, keys


def kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    epsilon = 1e-12
    p = np.clip(p, epsilon, 1)
    q = np.clip(q, epsilon, 1)

    return float(np.sum(p * np.log(p / q)))


def jensen_shannon_score(previous_counts: dict[str, int], current_counts: dict[str, int]) -> float:
    previous_distribution, current_distribution, _ = distribution_from_counts(
        previous_counts,
        current_counts,
    )

    if previous_distribution.sum() == 0 and current_distribution.sum() == 0:
        return 0.0

    midpoint = 0.5 * (previous_distribution + current_distribution)

    js_divergence = (
        0.5 * kl_divergence(previous_distribution, midpoint)
        + 0.5 * kl_divergence(current_distribution, midpoint)
    )

    # Natural-log JSD is bounded by ln(2). Normalise to 0..1.
    normalised = js_divergence / math.log(2)

    return round(max(0.0, min(1.0, normalised)), 4)


def novelty_ratio(previous_counts: dict[str, int], current_counts: dict[str, int]) -> float:
    previous_keys = set(previous_counts.keys())

    current_total = sum(current_counts.values())

    if current_total == 0:
        return 0.0

    novel_count = sum(
        count
        for key, count in current_counts.items()
        if key not in previous_keys
    )

    return round(novel_count / current_total, 4)


def dominant_key(counts: dict[str, int]) -> str | None:
    if not counts:
        return None

    return max(counts.items(), key=lambda item: item[1])[0]


def severity_from_score(score: float) -> str:
    if score >= 70:
        return "high"

    if score >= 45:
        return "medium"

    if score >= 25:
        return "low"

    return "info"


def calculate_drift_score(
    topic_drift: float,
    cluster_drift: float,
    novelty: float,
    risk_delta: float,
) -> float:
    positive_risk_delta = max(0.0, risk_delta)

    score = 100 * (
        0.40 * topic_drift
        + 0.35 * cluster_drift
        + 0.15 * novelty
        + 0.10 * min(1.0, positive_risk_delta)
    )

    return round(score, 2)


def save_topic_timeseries(
    profile_id: str,
    granularity: str,
    window_start: datetime,
    window_end: datetime,
    counts: dict[str, int],
    total: int,
):
    if total == 0:
        return

    rows = []

    for parent_label, watch_count in counts.items():
        rows.append(
            (
                profile_id,
                parent_label,
                granularity,
                window_start,
                window_end,
                watch_count,
                total,
                watch_count / total,
            )
        )

    query = """
        INSERT INTO profile_topic_exposure_timeseries (
            profile_id,
            parent_label,
            granularity,
            window_start,
            window_end,
            watch_count,
            total_watch_count,
            exposure_ratio
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (profile_id, parent_label, granularity, window_start, window_end)
        DO UPDATE SET
            watch_count = EXCLUDED.watch_count,
            total_watch_count = EXCLUDED.total_watch_count,
            exposure_ratio = EXCLUDED.exposure_ratio,
            calculated_at = CURRENT_TIMESTAMP
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.executemany(query, rows)
    finally:
        connection.close()


def save_cluster_timeseries(
    profile_id: str,
    granularity: str,
    window_start: datetime,
    window_end: datetime,
    counts: dict[str, int],
    total: int,
):
    if total == 0:
        return

    rows = []

    for cluster_id, watch_count in counts.items():
        rows.append(
            (
                profile_id,
                cluster_id,
                granularity,
                window_start,
                window_end,
                watch_count,
                total,
                watch_count / total,
            )
        )

    query = """
        INSERT INTO profile_cluster_exposure_timeseries (
            profile_id,
            cluster_id,
            granularity,
            window_start,
            window_end,
            watch_count,
            total_watch_count,
            exposure_ratio
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (profile_id, cluster_id, granularity, window_start, window_end)
        DO UPDATE SET
            watch_count = EXCLUDED.watch_count,
            total_watch_count = EXCLUDED.total_watch_count,
            exposure_ratio = EXCLUDED.exposure_ratio,
            calculated_at = CURRENT_TIMESTAMP
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.executemany(query, rows)
    finally:
        connection.close()


def save_drift_signal(row: dict):
    query = """
        INSERT INTO profile_temporal_drift_signals (
            profile_id,
            granularity,
            previous_window_start,
            previous_window_end,
            current_window_start,
            current_window_end,
            dominant_topic_before,
            dominant_topic_after,
            topic_drift_score,
            cluster_drift_score,
            novelty_ratio,
            risk_exposure_before,
            risk_exposure_after,
            risk_exposure_delta,
            drift_score,
            severity,
            explanation,
            model_version
        )
        VALUES (
            %(profile_id)s,
            %(granularity)s,
            %(previous_window_start)s,
            %(previous_window_end)s,
            %(current_window_start)s,
            %(current_window_end)s,
            %(dominant_topic_before)s,
            %(dominant_topic_after)s,
            %(topic_drift_score)s,
            %(cluster_drift_score)s,
            %(novelty_ratio)s,
            %(risk_exposure_before)s,
            %(risk_exposure_after)s,
            %(risk_exposure_delta)s,
            %(drift_score)s,
            %(severity)s,
            %(explanation)s,
            %(model_version)s
        )
        ON CONFLICT (profile_id, granularity, current_window_start, current_window_end)
        DO UPDATE SET
            dominant_topic_before = EXCLUDED.dominant_topic_before,
            dominant_topic_after = EXCLUDED.dominant_topic_after,
            topic_drift_score = EXCLUDED.topic_drift_score,
            cluster_drift_score = EXCLUDED.cluster_drift_score,
            novelty_ratio = EXCLUDED.novelty_ratio,
            risk_exposure_before = EXCLUDED.risk_exposure_before,
            risk_exposure_after = EXCLUDED.risk_exposure_after,
            risk_exposure_delta = EXCLUDED.risk_exposure_delta,
            drift_score = EXCLUDED.drift_score,
            severity = EXCLUDED.severity,
            explanation = EXCLUDED.explanation,
            model_version = EXCLUDED.model_version,
            calculated_at = CURRENT_TIMESTAMP
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, row)
    finally:
        connection.close()


def build_explanation(
    dominant_before: str | None,
    dominant_after: str | None,
    topic_drift: float,
    cluster_drift: float,
    novelty: float,
    risk_delta: float,
    drift_score: float,
) -> str:
    before = dominant_before or "No dominant topic"
    after = dominant_after or "No dominant topic"

    return (
        f"Viewing distribution shifted from '{before}' to '{after}'. "
        f"Topic drift={topic_drift:.3f}, cluster drift={cluster_drift:.3f}, "
        f"novelty ratio={novelty:.3f}, risk exposure delta={risk_delta:.3f}. "
        f"Overall temporal drift score={drift_score:.2f}. "
        f"This is a behavioural change signal for review, not a diagnosis."
    )


def calculate_for_profile(profile_id: str, granularity: str, periods: int):
    latest_watch_time = get_latest_watch_time(profile_id)

    if latest_watch_time is None:
        print(f"No watch events for profile: {profile_id}")
        return

    windows = build_periods(
        anchor_time=latest_watch_time,
        granularity=granularity,
        periods=periods,
    )

    topic_by_window = {}
    cluster_by_window = {}
    risk_by_window = {}

    for window_start, window_end in windows:
        topic_counts, topic_total = get_topic_counts(
            profile_id=profile_id,
            window_start=window_start,
            window_end=window_end,
        )

        cluster_counts, cluster_total = get_cluster_counts(
            profile_id=profile_id,
            window_start=window_start,
            window_end=window_end,
        )

        risk_exposure = get_risk_exposure(
            profile_id=profile_id,
            window_start=window_start,
            window_end=window_end,
        )

        save_topic_timeseries(
            profile_id=profile_id,
            granularity=granularity,
            window_start=window_start,
            window_end=window_end,
            counts=topic_counts,
            total=topic_total,
        )

        save_cluster_timeseries(
            profile_id=profile_id,
            granularity=granularity,
            window_start=window_start,
            window_end=window_end,
            counts=cluster_counts,
            total=cluster_total,
        )

        topic_by_window[(window_start, window_end)] = topic_counts
        cluster_by_window[(window_start, window_end)] = cluster_counts
        risk_by_window[(window_start, window_end)] = risk_exposure

    for index in range(1, len(windows)):
        previous_window = windows[index - 1]
        current_window = windows[index]

        previous_topic_counts = topic_by_window[previous_window]
        current_topic_counts = topic_by_window[current_window]

        previous_cluster_counts = cluster_by_window[previous_window]
        current_cluster_counts = cluster_by_window[current_window]

        topic_drift = jensen_shannon_score(
            previous_counts=previous_topic_counts,
            current_counts=current_topic_counts,
        )

        cluster_drift = jensen_shannon_score(
            previous_counts=previous_cluster_counts,
            current_counts=current_cluster_counts,
        )

        novelty = novelty_ratio(
            previous_counts=previous_cluster_counts,
            current_counts=current_cluster_counts,
        )

        risk_before = risk_by_window[previous_window]
        risk_after = risk_by_window[current_window]
        risk_delta = risk_after - risk_before

        dominant_before = dominant_key(previous_topic_counts)
        dominant_after = dominant_key(current_topic_counts)

        drift_score = calculate_drift_score(
            topic_drift=topic_drift,
            cluster_drift=cluster_drift,
            novelty=novelty,
            risk_delta=risk_delta,
        )

        severity = severity_from_score(drift_score)

        explanation = build_explanation(
            dominant_before=dominant_before,
            dominant_after=dominant_after,
            topic_drift=topic_drift,
            cluster_drift=cluster_drift,
            novelty=novelty,
            risk_delta=risk_delta,
            drift_score=drift_score,
        )

        row = {
            "profile_id": profile_id,
            "granularity": granularity,
            "previous_window_start": previous_window[0],
            "previous_window_end": previous_window[1],
            "current_window_start": current_window[0],
            "current_window_end": current_window[1],
            "dominant_topic_before": dominant_before,
            "dominant_topic_after": dominant_after,
            "topic_drift_score": topic_drift,
            "cluster_drift_score": cluster_drift,
            "novelty_ratio": novelty,
            "risk_exposure_before": round(risk_before, 4),
            "risk_exposure_after": round(risk_after, 4),
            "risk_exposure_delta": round(risk_delta, 4),
            "drift_score": drift_score,
            "severity": severity,
            "explanation": explanation,
            "model_version": MODEL_VERSION,
        }

        save_drift_signal(row)

        print(
            f"{profile_id} | {granularity} | "
            f"{current_window[0].date()} → {current_window[1].date()} | "
            f"topic_drift={topic_drift} | cluster_drift={cluster_drift} | "
            f"novelty={novelty} | drift_score={drift_score} | severity={severity}"
        )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--profile-id",
        default=None,
        help="Optional profile ID. If omitted, all profiles are processed.",
    )

    parser.add_argument(
        "--granularity",
        default="weekly",
        choices=["daily", "weekly", "monthly"],
    )

    parser.add_argument(
        "--periods",
        type=int,
        default=12,
        help="Number of recent periods to analyse.",
    )

    args = parser.parse_args()

    if args.profile_id:
        profiles = [args.profile_id]
    else:
        profiles = get_profiles()

    for profile_id in profiles:
        calculate_for_profile(
            profile_id=profile_id,
            granularity=args.granularity,
            periods=args.periods,
        )


if __name__ == "__main__":
    main()