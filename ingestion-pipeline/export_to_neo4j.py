import argparse
import os
from datetime import datetime
from typing import Any, Iterable

from neo4j import GraphDatabase

from db import get_connection


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def to_iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def chunked(items: list[dict], size: int) -> Iterable[list[dict]]:
    for index in range(0, len(items), size):
        yield items[index:index + size]


def fetch_rows(query: str, params: tuple = ()) -> list[dict]:
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                return [
                    {
                        column: to_iso(value)
                        for column, value in zip(columns, row)
                    }
                    for row in rows
                ]
    finally:
        connection.close()


def create_constraints(session):
    statements = [
        """
        CREATE CONSTRAINT profile_id_unique IF NOT EXISTS
        FOR (p:Profile)
        REQUIRE p.profile_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT video_id_unique IF NOT EXISTS
        FOR (v:Video)
        REQUIRE v.video_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT channel_id_unique IF NOT EXISTS
        FOR (c:Channel)
        REQUIRE c.channel_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT cluster_id_unique IF NOT EXISTS
        FOR (c:ContentCluster)
        REQUIRE c.cluster_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT parent_topic_name_unique IF NOT EXISTS
        FOR (t:ParentTopic)
        REQUIRE t.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT risk_category_name_unique IF NOT EXISTS
        FOR (r:RiskCategory)
        REQUIRE r.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT echo_signal_id_unique IF NOT EXISTS
        FOR (s:EchoSignal)
        REQUIRE s.signal_id IS UNIQUE
        """,
    ]

    for statement in statements:
        session.run(statement)


def clear_graph(session):
    session.run("MATCH (n) DETACH DELETE n")


def write_batch(session, query: str, rows: list[dict], batch_size: int = 1000):
    if not rows:
        return 0

    total = 0

    for batch in chunked(rows, batch_size):
        session.execute_write(
            lambda tx, batch_rows: tx.run(query, rows=batch_rows).consume(),
            batch,
        )
        total += len(batch)

    return total


def export_profiles(session):
    rows = fetch_rows(
        """
        SELECT
            profile_id,
            display_name,
            profile_type,
            created_at
        FROM profiles
        """
    )

    query = """
    UNWIND $rows AS row
    MERGE (p:Profile {profile_id: row.profile_id})
    SET
        p.display_name = row.display_name,
        p.profile_type = row.profile_type,
        p.created_at = row.created_at
    """

    count = write_batch(session, query, rows)
    print(f"Exported Profile nodes: {count}")


def export_channels(session):
    rows = fetch_rows(
        """
        SELECT DISTINCT
            channel_id,
            channel_title
        FROM youtube_videos
        WHERE channel_id IS NOT NULL
        """
    )

    query = """
    UNWIND $rows AS row
    MERGE (c:Channel {channel_id: row.channel_id})
    SET c.channel_title = row.channel_title
    """

    count = write_batch(session, query, rows)
    print(f"Exported Channel nodes: {count}")


def export_videos(session, limit: int | None):
    query = """
        SELECT
            video_id,
            title,
            description,
            channel_id,
            channel_title,
            published_at,
            category_id,
            duration,
            view_count,
            like_count,
            comment_count,
            thumbnail_url,
            collected_at
        FROM youtube_videos
        ORDER BY collected_at DESC
    """

    params = ()

    if limit:
        query += " LIMIT %s"
        params = (limit,)

    rows = fetch_rows(query, params)

    cypher = """
    UNWIND $rows AS row
    MERGE (v:Video {video_id: row.video_id})
    SET
        v.title = row.title,
        v.description = row.description,
        v.channel_id = row.channel_id,
        v.channel_title = row.channel_title,
        v.published_at = row.published_at,
        v.category_id = row.category_id,
        v.duration = row.duration,
        v.view_count = row.view_count,
        v.like_count = row.like_count,
        v.comment_count = row.comment_count,
        v.thumbnail_url = row.thumbnail_url,
        v.collected_at = row.collected_at
    """

    count = write_batch(session, cypher, rows)
    print(f"Exported Video nodes: {count}")


def export_video_channel_relationships(session):
    rows = fetch_rows(
        """
        SELECT
            video_id,
            channel_id
        FROM youtube_videos
        WHERE channel_id IS NOT NULL
        """
    )

    query = """
    UNWIND $rows AS row
    MATCH (v:Video {video_id: row.video_id})
    MATCH (c:Channel {channel_id: row.channel_id})
    MERGE (v)-[:PUBLISHED_BY]->(c)
    """

    count = write_batch(session, query, rows)
    print(f"Exported PUBLISHED_BY relationships: {count}")


def export_clusters(session):
    rows = fetch_rows(
        """
        SELECT
            cluster_id,
            cluster_label,
            raw_cluster_label,
            display_label,
            parent_label,
            parent_label_confidence,
            parent_label_margin,
            label_refinement_reason,
            label_source,
            summary,
            top_terms,
            keybert_keywords,
            video_count,
            model_version,
            created_at,
            updated_at
        FROM content_clusters
        """
    )

    query = """
    UNWIND $rows AS row
    MERGE (c:ContentCluster {cluster_id: row.cluster_id})
    SET
        c.cluster_label = row.cluster_label,
        c.raw_cluster_label = row.raw_cluster_label,
        c.display_label = row.display_label,
        c.parent_label = row.parent_label,
        c.parent_label_confidence = row.parent_label_confidence,
        c.parent_label_margin = row.parent_label_margin,
        c.label_refinement_reason = row.label_refinement_reason,
        c.label_source = row.label_source,
        c.summary = row.summary,
        c.top_terms = row.top_terms,
        c.keybert_keywords = row.keybert_keywords,
        c.video_count = row.video_count,
        c.model_version = row.model_version,
        c.created_at = row.created_at,
        c.updated_at = row.updated_at
    """

    count = write_batch(session, query, rows)
    print(f"Exported ContentCluster nodes: {count}")


def export_parent_topics(session):
    rows = fetch_rows(
        """
        SELECT DISTINCT
            parent_label
        FROM content_clusters
        WHERE parent_label IS NOT NULL
        """
    )

    rows = [
        {"name": row["parent_label"]}
        for row in rows
        if row["parent_label"]
    ]

    query = """
    UNWIND $rows AS row
    MERGE (t:ParentTopic {name: row.name})
    """

    count = write_batch(session, query, rows)
    print(f"Exported ParentTopic nodes: {count}")


def export_cluster_parent_relationships(session):
    rows = fetch_rows(
        """
        SELECT
            cluster_id,
            parent_label,
            parent_label_confidence,
            parent_label_margin
        FROM content_clusters
        WHERE parent_label IS NOT NULL
        """
    )

    query = """
    UNWIND $rows AS row
    MATCH (c:ContentCluster {cluster_id: row.cluster_id})
    MATCH (t:ParentTopic {name: row.parent_label})
    MERGE (c)-[r:HAS_PARENT_TOPIC]->(t)
    SET
        r.confidence = row.parent_label_confidence,
        r.margin = row.parent_label_margin
    """

    count = write_batch(session, query, rows)
    print(f"Exported HAS_PARENT_TOPIC relationships: {count}")


def export_video_cluster_relationships(session):
    rows = fetch_rows(
        """
        SELECT
            video_id,
            cluster_id,
            confidence,
            assigned_at
        FROM video_cluster_assignments
        """
    )

    query = """
    UNWIND $rows AS row
    MATCH (v:Video {video_id: row.video_id})
    MATCH (c:ContentCluster {cluster_id: row.cluster_id})
    MERGE (v)-[r:IN_CLUSTER]->(c)
    SET
        r.confidence = row.confidence,
        r.assigned_at = row.assigned_at
    """

    count = write_batch(session, query, rows)
    print(f"Exported IN_CLUSTER relationships: {count}")


def export_profile_watch_relationships(session):
    rows = fetch_rows(
        """
        SELECT
            profile_id,
            video_id,
            COUNT(*) AS watch_count,
            MIN(watched_at) AS first_watched_at,
            MAX(watched_at) AS last_watched_at
        FROM raw_watch_events
        GROUP BY profile_id, video_id
        """
    )

    query = """
    UNWIND $rows AS row
    MATCH (p:Profile {profile_id: row.profile_id})
    MATCH (v:Video {video_id: row.video_id})
    MERGE (p)-[r:WATCHED]->(v)
    SET
        r.watch_count = row.watch_count,
        r.first_watched_at = row.first_watched_at,
        r.last_watched_at = row.last_watched_at
    """

    count = write_batch(session, query, rows)
    print(f"Exported WATCHED relationships: {count}")


def export_similarity_relationships(
    session,
    similarity_threshold: float,
    similarity_limit: int,
):
    rows = fetch_rows(
        """
        SELECT
            source_video_id,
            target_video_id,
            similarity,
            model_name,
            created_at
        FROM video_similarity_edges
        WHERE similarity >= %s
        ORDER BY similarity DESC
        LIMIT %s
        """,
        (
            similarity_threshold,
            similarity_limit,
        ),
    )

    query = """
    UNWIND $rows AS row
    MATCH (source:Video {video_id: row.source_video_id})
    MATCH (target:Video {video_id: row.target_video_id})
    MERGE (source)-[r:SIMILAR_TO]->(target)
    SET
        r.similarity = row.similarity,
        r.model_name = row.model_name,
        r.created_at = row.created_at
    """

    count = write_batch(session, query, rows)
    print(f"Exported SIMILAR_TO relationships: {count}")


def export_risk_categories(session):
    rows = fetch_rows(
        """
        SELECT DISTINCT
            inferred_risk_category
        FROM cluster_taxonomy_labels
        WHERE inferred_risk_category IS NOT NULL
        """
    )

    rows = [
        {"name": row["inferred_risk_category"]}
        for row in rows
        if row["inferred_risk_category"]
    ]

    query = """
    UNWIND $rows AS row
    MERGE (r:RiskCategory {name: row.name})
    """

    count = write_batch(session, query, rows)
    print(f"Exported RiskCategory nodes: {count}")


def export_cluster_risk_relationships(session):
    rows = fetch_rows(
        """
        SELECT
            cluster_id,
            inferred_topic,
            inferred_risk_category,
            risk_score,
            confidence,
            explanation,
            model_version,
            labelled_at
        FROM cluster_taxonomy_labels
        WHERE inferred_risk_category IS NOT NULL
        """
    )

    query = """
    UNWIND $rows AS row
    MATCH (c:ContentCluster {cluster_id: row.cluster_id})
    MATCH (r:RiskCategory {name: row.inferred_risk_category})
    MERGE (c)-[rel:MAPPED_TO]->(r)
    SET
        rel.inferred_topic = row.inferred_topic,
        rel.risk_score = row.risk_score,
        rel.confidence = row.confidence,
        rel.explanation = row.explanation,
        rel.model_version = row.model_version,
        rel.labelled_at = row.labelled_at
    """

    count = write_batch(session, query, rows)
    print(f"Exported MAPPED_TO relationships: {count}")


def export_echo_signals(session, window_days: int | None):
    query = """
        SELECT
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
        FROM echo_chamber_scores
    """

    params = ()

    if window_days:
        query += " WHERE window_days = %s"
        params = (window_days,)

    rows = fetch_rows(query, params)

    for row in rows:
        row["signal_id"] = (
            f"{row['profile_id']}|{row['cluster_id']}|{row['window_days']}"
        )

    node_query = """
    UNWIND $rows AS row
    MERGE (s:EchoSignal {signal_id: row.signal_id})
    SET
        s.profile_id = row.profile_id,
        s.cluster_id = row.cluster_id,
        s.window_days = row.window_days,
        s.current_watch_count = row.current_watch_count,
        s.current_total_watch_count = row.current_total_watch_count,
        s.current_exposure_ratio = row.current_exposure_ratio,
        s.previous_exposure_ratio = row.previous_exposure_ratio,
        s.trend_delta = row.trend_delta,
        s.inferred_risk_category = row.inferred_risk_category,
        s.taxonomy_risk_score = row.taxonomy_risk_score,
        s.echo_score = row.echo_score,
        s.severity = row.severity,
        s.explanation = row.explanation,
        s.model_version = row.model_version,
        s.calculated_at = row.calculated_at
    """

    signal_count = write_batch(session, node_query, rows)
    print(f"Exported EchoSignal nodes: {signal_count}")

    profile_rel_query = """
    UNWIND $rows AS row
    MATCH (p:Profile {profile_id: row.profile_id})
    MATCH (s:EchoSignal {signal_id: row.signal_id})
    MERGE (p)-[:HAS_ECHO_SIGNAL]->(s)
    """

    profile_rel_count = write_batch(session, profile_rel_query, rows)
    print(f"Exported HAS_ECHO_SIGNAL relationships: {profile_rel_count}")

    cluster_rel_query = """
    UNWIND $rows AS row
    MATCH (s:EchoSignal {signal_id: row.signal_id})
    MATCH (c:ContentCluster {cluster_id: row.cluster_id})
    MERGE (s)-[:ABOUT_CLUSTER]->(c)
    """

    cluster_rel_count = write_batch(session, cluster_rel_query, rows)
    print(f"Exported ABOUT_CLUSTER relationships: {cluster_rel_count}")


def export_all(args):
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )

    try:
        with driver.session() as session:
            print("Creating Neo4j constraints...")
            create_constraints(session)

            if args.clear:
                print("Clearing existing Neo4j graph...")
                clear_graph(session)

            export_profiles(session)
            export_channels(session)
            export_videos(session, limit=args.video_limit)
            export_video_channel_relationships(session)

            export_clusters(session)
            export_parent_topics(session)
            export_cluster_parent_relationships(session)
            export_video_cluster_relationships(session)

            export_profile_watch_relationships(session)

            export_similarity_relationships(
                session=session,
                similarity_threshold=args.similarity_threshold,
                similarity_limit=args.similarity_limit,
            )

            export_risk_categories(session)
            export_cluster_risk_relationships(session)

            export_echo_signals(
                session=session,
                window_days=args.window_days,
            )

            print("Neo4j export complete.")

    finally:
        driver.close()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete all existing Neo4j nodes and relationships before export.",
    )

    parser.add_argument(
        "--video-limit",
        type=int,
        default=None,
        help="Optional limit for exported videos.",
    )

    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.75,
        help="Only export SIMILAR_TO edges above this similarity.",
    )

    parser.add_argument(
        "--similarity-limit",
        type=int,
        default=50000,
        help="Maximum number of SIMILAR_TO relationships to export.",
    )

    parser.add_argument(
        "--window-days",
        type=int,
        default=None,
        help="Optional echo score window to export.",
    )

    args = parser.parse_args()

    print(f"Neo4j URI: {NEO4J_URI}")
    export_all(args)


if __name__ == "__main__":
    main()