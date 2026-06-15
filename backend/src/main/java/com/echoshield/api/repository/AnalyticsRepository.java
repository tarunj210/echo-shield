package com.echoshield.api.repository;

import com.echoshield.api.dto.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class AnalyticsRepository {

    private final JdbcTemplate jdbcTemplate;

    public AnalyticsRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<ProfileDto> findProfiles() {
        String sql = """
            SELECT profile_id, display_name, profile_type, created_at
            FROM profiles
            ORDER BY created_at DESC
        """;

        return jdbcTemplate.query(sql, (rs, rowNum) -> new ProfileDto(
            rs.getString("profile_id"),
            rs.getString("display_name"),
            rs.getString("profile_type"),
            rs.getTimestamp("created_at") == null ? null : rs.getTimestamp("created_at").toLocalDateTime()
        ));
    }

    public ProfileOverviewDto getProfileOverview(String profileId) {
        String sql = """
            WITH watch_stats AS (
                SELECT
                    profile_id,
                    COUNT(*) AS total_watch_events,
                    COUNT(DISTINCT video_id) AS unique_videos
                FROM raw_watch_events
                WHERE profile_id = ?
                GROUP BY profile_id
            ),
            cluster_stats AS (
                SELECT
                    e.profile_id,
                    COUNT(DISTINCT a.cluster_id) AS unique_clusters
                FROM raw_watch_events e
                JOIN video_cluster_assignments a
                    ON e.video_id = a.video_id
                WHERE e.profile_id = ?
                GROUP BY e.profile_id
            ),
            signal_stats AS (
                SELECT
                    profile_id,
                    COUNT(*) AS review_signals,
                    MAX(echo_score) AS top_echo_score
                FROM echo_chamber_scores
                WHERE profile_id = ?
                GROUP BY profile_id
            ),
            top_signal AS (
                SELECT
                    profile_id,
                    severity AS top_severity
                FROM echo_chamber_scores
                WHERE profile_id = ?
                ORDER BY echo_score DESC
                LIMIT 1
            ),
            dominant_topic AS (
                SELECT
                    profile_id,
                    parent_label AS dominant_parent_topic
                FROM profile_topic_exposure_timeseries
                WHERE profile_id = ?
                ORDER BY window_end DESC, exposure_ratio DESC
                LIMIT 1
            )
            SELECT
                COALESCE(w.profile_id, ?) AS profile_id,
                COALESCE(w.total_watch_events, 0) AS total_watch_events,
                COALESCE(w.unique_videos, 0) AS unique_videos,
                COALESCE(c.unique_clusters, 0) AS unique_clusters,
                COALESCE(s.review_signals, 0) AS review_signals,
                s.top_echo_score,
                ts.top_severity,
                dt.dominant_parent_topic
            FROM watch_stats w
            LEFT JOIN cluster_stats c ON w.profile_id = c.profile_id
            LEFT JOIN signal_stats s ON w.profile_id = s.profile_id
            LEFT JOIN top_signal ts ON w.profile_id = ts.profile_id
            LEFT JOIN dominant_topic dt ON w.profile_id = dt.profile_id
        """;

        return jdbcTemplate.queryForObject(
            sql,
            (rs, rowNum) -> new ProfileOverviewDto(
                rs.getString("profile_id"),
                rs.getLong("total_watch_events"),
                rs.getLong("unique_videos"),
                rs.getLong("unique_clusters"),
                rs.getLong("review_signals"),
                rs.getObject("top_echo_score", Double.class),
                rs.getString("top_severity"),
                rs.getString("dominant_parent_topic")
            ),
            profileId,
            profileId,
            profileId,
            profileId,
            profileId,
            profileId
        );
    }

    public List<EchoSignalDto> getEchoSignals(String profileId, int limit) {
        String sql = """
            SELECT
                s.profile_id,
                s.cluster_id,
                COALESCE(c.display_label, c.cluster_label) AS display_label,
                c.parent_label,
                s.current_watch_count,
                s.current_total_watch_count,
                s.current_exposure_ratio,
                s.previous_exposure_ratio,
                s.trend_delta,
                s.inferred_risk_category,
                s.taxonomy_risk_score,
                s.echo_score,
                s.severity,
                s.explanation,
                s.calculated_at
            FROM echo_chamber_scores s
            JOIN content_clusters c
                ON s.cluster_id = c.cluster_id
            WHERE s.profile_id = ?
            ORDER BY s.echo_score DESC
            LIMIT ?
        """;

        return jdbcTemplate.query(sql, (rs, rowNum) -> new EchoSignalDto(
            rs.getString("profile_id"),
            rs.getString("cluster_id"),
            rs.getString("display_label"),
            rs.getString("parent_label"),
            rs.getObject("current_watch_count", Integer.class),
            rs.getObject("current_total_watch_count", Integer.class),
            rs.getObject("current_exposure_ratio", Double.class),
            rs.getObject("previous_exposure_ratio", Double.class),
            rs.getObject("trend_delta", Double.class),
            rs.getString("inferred_risk_category"),
            rs.getObject("taxonomy_risk_score", Double.class),
            rs.getObject("echo_score", Double.class),
            rs.getString("severity"),
            rs.getString("explanation"),
            rs.getTimestamp("calculated_at") == null ? null : rs.getTimestamp("calculated_at").toLocalDateTime()
        ), profileId, limit);
    }

    public List<TemporalDriftDto> getTemporalDrift(String profileId, String granularity, int limit) {
        String sql = """
            SELECT
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
                explanation
            FROM profile_temporal_drift_signals
            WHERE profile_id = ?
              AND granularity = ?
            ORDER BY current_window_start DESC
            LIMIT ?
        """;

        return jdbcTemplate.query(sql, (rs, rowNum) -> new TemporalDriftDto(
            rs.getString("profile_id"),
            rs.getString("granularity"),
            rs.getTimestamp("previous_window_start").toLocalDateTime(),
            rs.getTimestamp("previous_window_end").toLocalDateTime(),
            rs.getTimestamp("current_window_start").toLocalDateTime(),
            rs.getTimestamp("current_window_end").toLocalDateTime(),
            rs.getString("dominant_topic_before"),
            rs.getString("dominant_topic_after"),
            rs.getObject("topic_drift_score", Double.class),
            rs.getObject("cluster_drift_score", Double.class),
            rs.getObject("novelty_ratio", Double.class),
            rs.getObject("risk_exposure_before", Double.class),
            rs.getObject("risk_exposure_after", Double.class),
            rs.getObject("risk_exposure_delta", Double.class),
            rs.getObject("drift_score", Double.class),
            rs.getString("severity"),
            rs.getString("explanation")
        ), profileId, granularity, limit);
    }

    public List<TopicExposurePointDto> getTopicTimeseries(String profileId, String granularity) {
        String sql = """
            SELECT
                profile_id,
                parent_label,
                granularity,
                window_start,
                window_end,
                watch_count,
                total_watch_count,
                exposure_ratio
            FROM profile_topic_exposure_timeseries
            WHERE profile_id = ?
              AND granularity = ?
            ORDER BY window_start ASC, exposure_ratio DESC
        """;

        return jdbcTemplate.query(sql, (rs, rowNum) -> new TopicExposurePointDto(
            rs.getString("profile_id"),
            rs.getString("parent_label"),
            rs.getString("granularity"),
            rs.getTimestamp("window_start").toLocalDateTime(),
            rs.getTimestamp("window_end").toLocalDateTime(),
            rs.getObject("watch_count", Integer.class),
            rs.getObject("total_watch_count", Integer.class),
            rs.getObject("exposure_ratio", Double.class)
        ), profileId, granularity);
    }

    public List<ClusterVideoDto> getClusterVideos(String clusterId, int limit) {
        String sql = """
            SELECT
                y.video_id,
                y.title,
                y.channel_title,
                y.thumbnail_url,
                y.view_count,
                y.like_count
            FROM video_cluster_assignments a
            JOIN youtube_videos y
                ON a.video_id = y.video_id
            WHERE a.cluster_id = ?
            ORDER BY y.view_count DESC NULLS LAST
            LIMIT ?
        """;

        return jdbcTemplate.query(sql, (rs, rowNum) -> new ClusterVideoDto(
            rs.getString("video_id"),
            rs.getString("title"),
            rs.getString("channel_title"),
            rs.getString("thumbnail_url"),
            rs.getObject("view_count", Long.class),
            rs.getObject("like_count", Long.class)
        ), clusterId, limit);
    }
}