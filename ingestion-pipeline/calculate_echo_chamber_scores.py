import argparse
from datetime import timedelta
from typing import Optional

from db import get_connection


MODEL_VERSION = "echo_chamber_score_v1"


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


def get_profile_anchor_time(profile_id: str):
    """
    Uses the latest watch timestamp for the profile as the analysis anchor.

    This is better than NOW() for Google Takeout data because the export may contain
    historical watch events rather than current-day events.
    """
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


def calculate_cluster_exposure(
    profile_id: str,
    window_start,
    window_end,
) -> tuple[int, list[dict]]:
    """
    Denominator is clustered watch events only.

    Videos that do not have cluster assignments are ignored because they cannot
    contribute to semantic concentration.
    """
    query = """
        WITH clustered_events AS (
            SELECT
                r.video_id,
                a.cluster_id
            FROM raw_watch_events r
            JOIN video_cluster_assignments a
                ON r.video_id = a.video_id
            WHERE r.profile_id = %s
              AND r.watched_at >= %s
              AND r.watched_at < %s
        ),
        total AS (
            SELECT COUNT(*) AS total_watch_count
            FROM clustered_events
        ),
        cluster_counts AS (
            SELECT
                cluster_id,
                COUNT(*) AS watch_count
            FROM clustered_events
            GROUP BY cluster_id
        )
        SELECT
            c.cluster_id,
            c.watch_count,
            t.total_watch_count,
            CASE
                WHEN t.total_watch_count = 0 THEN 0
                ELSE c.watch_count::DOUBLE PRECISION / t.total_watch_count
            END AS exposure_ratio
        FROM cluster_counts c
        CROSS JOIN total t
        ORDER BY exposure_ratio DESC
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        profile_id,
                        window_start,
                        window_end,
                    ),
                )

                rows = cursor.fetchall()

                if not rows:
                    return 0, []

                total_watch_count = int(rows[0][2])

                exposure_rows = [
                    {
                        "cluster_id": row[0],
                        "watch_count": int(row[1]),
                        "total_watch_count": int(row[2]),
                        "exposure_ratio": float(row[3]),
                    }
                    for row in rows
                ]

                return total_watch_count, exposure_rows
    finally:
        connection.close()


def save_exposure_window(
    profile_id: str,
    window_days: int,
    window_type: str,
    window_start,
    window_end,
    exposure_rows: list[dict],
):
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM profile_cluster_exposure_windows
                    WHERE profile_id = %s
                      AND window_days = %s
                      AND window_type = %s
                    """,
                    (
                        profile_id,
                        window_days,
                        window_type,
                    ),
                )

                for row in exposure_rows:
                    cursor.execute(
                        """
                        INSERT INTO profile_cluster_exposure_windows (
                            profile_id,
                            cluster_id,
                            window_days,
                            window_type,
                            window_start,
                            window_end,
                            watch_count,
                            total_watch_count,
                            exposure_ratio,
                            calculated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """,
                        (
                            profile_id,
                            row["cluster_id"],
                            window_days,
                            window_type,
                            window_start,
                            window_end,
                            row["watch_count"],
                            row["total_watch_count"],
                            row["exposure_ratio"],
                        ),
                    )
    finally:
        connection.close()


def get_taxonomy_lookup() -> dict[str, dict]:
    query = """
        SELECT
            cluster_id,
            inferred_risk_category,
            risk_score
        FROM cluster_taxonomy_labels
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

                return {
                    row[0]: {
                        "inferred_risk_category": row[1],
                        "risk_score": float(row[2]) if row[2] is not None else 0.10,
                    }
                    for row in cursor.fetchall()
                }
    finally:
        connection.close()


def get_cluster_label_lookup() -> dict[str, str]:
    query = """
        SELECT cluster_id, cluster_label
        FROM content_clusters
    """

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

                return {
                    row[0]: row[1]
                    for row in cursor.fetchall()
                }
    finally:
        connection.close()


def calculate_score(
    current_exposure_ratio: float,
    previous_exposure_ratio: float,
    taxonomy_risk_score: float,
) -> tuple[float, float]:
    """
    Score components:
      55% current concentration
      25% positive trend increase
      20% optional taxonomy risk

    Trend is normalized so a +30 percentage point increase becomes full trend signal.
    """
    trend_delta = current_exposure_ratio - previous_exposure_ratio
    positive_trend = max(0.0, trend_delta)

    trend_signal = min(1.0, positive_trend / 0.30)

    echo_score = 100.0 * (
        0.55 * current_exposure_ratio
        + 0.25 * trend_signal
        + 0.20 * taxonomy_risk_score
    )

    echo_score = round(max(0.0, min(echo_score, 100.0)), 2)

    return echo_score, round(trend_delta, 4)


def severity_from_score(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    if score >= 25:
        return "low"
    return "info"


def build_explanation(
    cluster_label: Optional[str],
    current_watch_count: int,
    current_total_watch_count: int,
    current_exposure_ratio: float,
    previous_exposure_ratio: float,
    trend_delta: float,
    risk_category: str,
    taxonomy_risk_score: float,
    echo_score: float,
    severity: str,
) -> str:
    exposure_percent = round(current_exposure_ratio * 100, 1)
    previous_percent = round(previous_exposure_ratio * 100, 1)
    trend_percent = round(trend_delta * 100, 1)

    label = cluster_label or "Unnamed semantic cluster"

    if trend_delta >= 0:
        trend_text = f"increased by {trend_percent} percentage points"
    else:
        trend_text = f"decreased by {abs(trend_percent)} percentage points"

    return (
        f"{severity.upper()} signal for cluster '{label}'. "
        f"{current_watch_count}/{current_total_watch_count} clustered watch events "
        f"({exposure_percent}%) in the current window belong to this cluster. "
        f"Previous-window exposure was {previous_percent}%, so exposure {trend_text}. "
        f"Optional taxonomy category: {risk_category} "
        f"(risk score {taxonomy_risk_score:.2f}). "
        f"Echo score: {echo_score:.2f}/100. "
        f"This is an explainable review signal, not a diagnosis or moderation decision."
    )


def save_scores(
    profile_id: str,
    window_days: int,
    scores: list[dict],
):
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM echo_chamber_scores
                    WHERE profile_id = %s
                      AND window_days = %s
                    """,
                    (
                        profile_id,
                        window_days,
                    ),
                )

                for score in scores:
                    cursor.execute(
                        """
                        INSERT INTO echo_chamber_scores (
                            profile_id,
                            cluster_id,
                            window_days,
                            current_watch_count,
                            current_total_watch_count,
                            current_exposure_ratio,
                            previous_exposure_ratio,
                            trend_delta,
                            inferred_risk_category,
                            taxonomy_risk_score,
                            echo_score,
                            severity,
                            explanation,
                            model_version,
                            calculated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """,
                        (
                            profile_id,
                            score["cluster_id"],
                            window_days,
                            score["current_watch_count"],
                            score["current_total_watch_count"],
                            score["current_exposure_ratio"],
                            score["previous_exposure_ratio"],
                            score["trend_delta"],
                            score["inferred_risk_category"],
                            score["taxonomy_risk_score"],
                            score["echo_score"],
                            score["severity"],
                            score["explanation"],
                            MODEL_VERSION,
                        ),
                    )
    finally:
        connection.close()


def score_profile(
    profile_id: str,
    window_days: int,
    min_watch_count: int,
    min_score: float,
) -> list[dict]:
    anchor_time = get_profile_anchor_time(profile_id)

    if anchor_time is None:
        print(f"{profile_id}: no watch events found")
        return []

    # Include the latest event by adding one second to the upper bound.
    current_end = anchor_time + timedelta(seconds=1)
    current_start = current_end - timedelta(days=window_days)

    previous_end = current_start
    previous_start = previous_end - timedelta(days=window_days)

    print(f"{profile_id}: current window {current_start} -> {current_end}")
    print(f"{profile_id}: previous window {previous_start} -> {previous_end}")

    _, current_exposure = calculate_cluster_exposure(
        profile_id=profile_id,
        window_start=current_start,
        window_end=current_end,
    )

    _, previous_exposure = calculate_cluster_exposure(
        profile_id=profile_id,
        window_start=previous_start,
        window_end=previous_end,
    )

    save_exposure_window(
        profile_id=profile_id,
        window_days=window_days,
        window_type="current",
        window_start=current_start,
        window_end=current_end,
        exposure_rows=current_exposure,
    )

    save_exposure_window(
        profile_id=profile_id,
        window_days=window_days,
        window_type="previous",
        window_start=previous_start,
        window_end=previous_end,
        exposure_rows=previous_exposure,
    )

    previous_lookup = {
        row["cluster_id"]: row
        for row in previous_exposure
    }

    taxonomy_lookup = get_taxonomy_lookup()
    cluster_label_lookup = get_cluster_label_lookup()

    scores = []

    for current_row in current_exposure:
        cluster_id = current_row["cluster_id"]
        current_watch_count = current_row["watch_count"]
        current_total_watch_count = current_row["total_watch_count"]
        current_exposure_ratio = current_row["exposure_ratio"]

        if current_watch_count < min_watch_count:
            continue

        previous_row = previous_lookup.get(cluster_id)
        previous_exposure_ratio = (
            previous_row["exposure_ratio"]
            if previous_row
            else 0.0
        )

        taxonomy = taxonomy_lookup.get(
            cluster_id,
            {
                "inferred_risk_category": "low_or_unknown",
                "risk_score": 0.10,
            },
        )

        risk_category = taxonomy["inferred_risk_category"] or "low_or_unknown"
        taxonomy_risk_score = taxonomy["risk_score"] or 0.10

        echo_score, trend_delta = calculate_score(
            current_exposure_ratio=current_exposure_ratio,
            previous_exposure_ratio=previous_exposure_ratio,
            taxonomy_risk_score=taxonomy_risk_score,
        )

        if echo_score < min_score:
            continue

        severity = severity_from_score(echo_score)

        explanation = build_explanation(
            cluster_label=cluster_label_lookup.get(cluster_id),
            current_watch_count=current_watch_count,
            current_total_watch_count=current_total_watch_count,
            current_exposure_ratio=current_exposure_ratio,
            previous_exposure_ratio=previous_exposure_ratio,
            trend_delta=trend_delta,
            risk_category=risk_category,
            taxonomy_risk_score=taxonomy_risk_score,
            echo_score=echo_score,
            severity=severity,
        )

        scores.append({
            "cluster_id": cluster_id,
            "current_watch_count": current_watch_count,
            "current_total_watch_count": current_total_watch_count,
            "current_exposure_ratio": current_exposure_ratio,
            "previous_exposure_ratio": previous_exposure_ratio,
            "trend_delta": trend_delta,
            "inferred_risk_category": risk_category,
            "taxonomy_risk_score": taxonomy_risk_score,
            "echo_score": echo_score,
            "severity": severity,
            "explanation": explanation,
        })

    scores = sorted(
        scores,
        key=lambda row: row["echo_score"],
        reverse=True,
    )

    save_scores(
        profile_id=profile_id,
        window_days=window_days,
        scores=scores,
    )

    return scores


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--profile-id",
        default=None,
        help="Profile to score. If omitted, scores all profiles.",
    )

    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Window size in days.",
    )

    parser.add_argument(
        "--min-watch-count",
        type=int,
        default=5,
        help="Minimum cluster watch count required to score a cluster.",
    )

    parser.add_argument(
        "--min-score",
        type=float,
        default=25.0,
        help="Minimum echo score required to persist a score row.",
    )

    args = parser.parse_args()

    if args.profile_id:
        profiles = [args.profile_id]
    else:
        profiles = get_profiles()

    print(f"Profiles to score: {profiles}")
    print(f"Window days: {args.window_days}")

    for profile_id in profiles:
        scores = score_profile(
            profile_id=profile_id,
            window_days=args.window_days,
            min_watch_count=args.min_watch_count,
            min_score=args.min_score,
        )

        print(f"\n{profile_id}: saved {len(scores)} echo chamber score rows")

        for score in scores[:10]:
            print(
                f"  {score['cluster_id']} | "
                f"score={score['echo_score']} | "
                f"severity={score['severity']} | "
                f"exposure={score['current_exposure_ratio']:.3f} | "
                f"trend={score['trend_delta']:.3f} | "
                f"risk={score['inferred_risk_category']}"
            )


if __name__ == "__main__":
    main()