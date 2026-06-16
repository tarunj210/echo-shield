package com.echoshield.api.repository;

import com.echoshield.api.dto.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

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
            rs.getTimestamp("created_at") == null
                ? null
                : rs.getTimestamp("created_at").toLocalDateTime()
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
            LEFT JOIN cluster_stats c
                ON w.profile_id = c.profile_id
            LEFT JOIN signal_stats s
                ON w.profile_id = s.profile_id
            LEFT JOIN top_signal ts
                ON w.profile_id = ts.profile_id
            LEFT JOIN dominant_topic dt
                ON w.profile_id = dt.profile_id
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
            rs.getTimestamp("calculated_at") == null
                ? null
                : rs.getTimestamp("calculated_at").toLocalDateTime()
        ), profileId, limit);
    }

    public List<TemporalDriftDto> getTemporalDrift(
        String profileId,
        String granularity,
        int limit
    ) {
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

    public List<TopicExposurePointDto> getTopicTimeseries(
        String profileId,
        String granularity
    ) {
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

    public List<WatchSessionDto> getWatchSessions(String profileId, int limit) {
        String sql = """
            SELECT
                session_id,
                profile_id,
                session_index,
                session_start,
                session_end,
                video_count,
                unique_channel_count,
                dominant_channel_title,
                total_duration_minutes
            FROM profile_watch_sessions
            WHERE profile_id = ?
            ORDER BY session_start DESC
            LIMIT ?
        """;

        return jdbcTemplate.query(
            sql,
            (rs, rowNum) -> new WatchSessionDto(
                rs.getString("session_id"),
                rs.getString("profile_id"),
                rs.getInt("session_index"),
                rs.getTimestamp("session_start").toLocalDateTime(),
                rs.getTimestamp("session_end").toLocalDateTime(),
                rs.getInt("video_count"),
                rs.getInt("unique_channel_count"),
                rs.getString("dominant_channel_title"),
                rs.getInt("total_duration_minutes")
            ),
            profileId,
            limit
        );
    }

    public SessionTrajectoryDto getSessionTrajectory(
        String profileId,
        String sessionId
    ) {
        String sql = """
            SELECT
                a.event_id::text AS event_id,
                a.sequence_in_session,
                a.minutes_since_previous,
                r.video_id,
                r.watched_at,
                r.raw_title,
                y.title,
                y.channel_id,
                y.channel_title,
                y.thumbnail_url
            FROM watch_event_session_assignments a
            JOIN raw_watch_events r
                ON r.event_id = a.event_id
            LEFT JOIN youtube_videos y
                ON y.video_id = r.video_id
            WHERE a.profile_id = ?
              AND a.session_id = ?
            ORDER BY a.sequence_in_session ASC
        """;

        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
            sql,
            profileId,
            sessionId
        );

        List<SessionTrajectoryDto.TrajectoryNodeDto> nodes = new ArrayList<>();
        List<SessionTrajectoryDto.TrajectoryEdgeDto> edges = new ArrayList<>();
        List<SessionTrajectoryDto.TrajectoryTimelineItemDto> timeline =
            new ArrayList<>();

        Set<String> addedNodeIds = new HashSet<>();

        String previousEventNodeId = null;

        for (Map<String, Object> row : rows) {
            String eventId = (String) row.get("event_id");
            String videoId = (String) row.get("video_id");
            String channelId = (String) row.get("channel_id");

            String title = row.get("title") != null
                ? (String) row.get("title")
                : (String) row.get("raw_title");

            if (title == null || title.isBlank()) {
                title = "Untitled video";
            }

            String channelTitle = row.get("channel_title") != null
                ? (String) row.get("channel_title")
                : "Unknown Channel";

            String thumbnailUrl = (String) row.get("thumbnail_url");

            LocalDateTime watchedAt = toLocalDateTime(row.get("watched_at"));

            Integer sequenceIndex = row.get("sequence_in_session") == null
                ? null
                : ((Number) row.get("sequence_in_session")).intValue();

            Integer minutesSincePrevious = row.get("minutes_since_previous") == null
                ? null
                : ((Number) row.get("minutes_since_previous")).intValue();

            String eventNodeId = "event_" + eventId;
            String videoNodeId = "video_" + videoId;
            String channelNodeId = channelId != null
                ? "channel_" + channelId
                : null;

            if (addedNodeIds.add(eventNodeId)) {
                nodes.add(new SessionTrajectoryDto.TrajectoryNodeDto(
                    eventNodeId,
                    "watch_event",
                    "Watch " + sequenceIndex,
                    videoId,
                    channelId,
                    channelTitle,
                    null,
                    watchedAt,
                    sequenceIndex
                ));
            }

            if (addedNodeIds.add(videoNodeId)) {
                nodes.add(new SessionTrajectoryDto.TrajectoryNodeDto(
                    videoNodeId,
                    "video",
                    title,
                    videoId,
                    channelId,
                    channelTitle,
                    thumbnailUrl,
                    watchedAt,
                    sequenceIndex
                ));
            }

            if (channelNodeId != null && addedNodeIds.add(channelNodeId)) {
                nodes.add(new SessionTrajectoryDto.TrajectoryNodeDto(
                    channelNodeId,
                    "channel",
                    channelTitle,
                    null,
                    channelId,
                    channelTitle,
                    null,
                    null,
                    null
                ));
            }

            if (previousEventNodeId != null) {
                edges.add(new SessionTrajectoryDto.TrajectoryEdgeDto(
                    previousEventNodeId,
                    eventNodeId,
                    "NEXT_WATCH",
                    minutesSincePrevious
                ));
            }

            edges.add(new SessionTrajectoryDto.TrajectoryEdgeDto(
                eventNodeId,
                videoNodeId,
                "WATCHED_VIDEO",
                null
            ));

            if (channelNodeId != null) {
                edges.add(new SessionTrajectoryDto.TrajectoryEdgeDto(
                    videoNodeId,
                    channelNodeId,
                    "PUBLISHED_BY",
                    null
                ));
            }

            timeline.add(new SessionTrajectoryDto.TrajectoryTimelineItemDto(
                eventId,
                videoId,
                title,
                channelTitle,
                thumbnailUrl,
                watchedAt,
                minutesSincePrevious,
                sequenceIndex
            ));

            previousEventNodeId = eventNodeId;
        }

        return new SessionTrajectoryDto(
            profileId,
            sessionId,
            nodes,
            edges,
            timeline
        );
    }

    public SessionSummaryGraphDto getSessionSummaryGraph(
        String profileId,
        int limit
    ) {
        String topicExpression = """
            COALESCE(
                NULLIF(c.parent_label, ''),
                CASE CAST(y.category_id AS TEXT)
                    WHEN '1' THEN 'Movies & Television'
                    WHEN '2' THEN 'Autos & Vehicles'
                    WHEN '10' THEN 'Music & Performance'
                    WHEN '15' THEN 'Science & Nature'
                    WHEN '17' THEN 'Sports'
                    WHEN '19' THEN 'Travel & Places'
                    WHEN '20' THEN 'Gaming'
                    WHEN '22' THEN 'Social & Lifestyle'
                    WHEN '23' THEN 'Entertainment & Commentary'
                    WHEN '24' THEN 'Entertainment & Commentary'
                    WHEN '25' THEN 'News & Current Affairs'
                    WHEN '26' THEN 'Social & Lifestyle'
                    WHEN '27' THEN 'Education & Learning'
                    WHEN '28' THEN 'Technology & Computing'
                    ELSE 'General / Mixed'
                END
            )
        """;

        String nodeSql = """
            WITH selected_sessions AS (
                SELECT *
                FROM profile_watch_sessions
                WHERE profile_id = ?
                ORDER BY session_start DESC
                LIMIT ?
            ),
            session_event_topics AS (
                SELECT
                    a.session_id,
                    __TOPIC_EXPRESSION__ AS parent_topic
                FROM watch_event_session_assignments a
                JOIN raw_watch_events r
                    ON r.event_id = a.event_id
                LEFT JOIN youtube_videos y
                    ON y.video_id = r.video_id
                LEFT JOIN video_cluster_assignments vca
                    ON vca.video_id = r.video_id
                LEFT JOIN content_clusters c
                    ON c.cluster_id = vca.cluster_id
                WHERE a.profile_id = ?
                  AND a.session_id IN (
                      SELECT session_id
                      FROM selected_sessions
                  )
            ),
            session_topics AS (
                SELECT
                    session_id,
                    parent_topic,
                    COUNT(*) AS topic_video_count
                FROM session_event_topics
                GROUP BY session_id, parent_topic
            ),
            ranked_topics AS (
                SELECT
                    session_id,
                    parent_topic,
                    topic_video_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY session_id
                        ORDER BY topic_video_count DESC, parent_topic ASC
                    ) AS rn
                FROM session_topics
            )
            SELECT
                s.session_id,
                s.profile_id,
                s.session_index,
                s.session_start,
                s.session_end,
                s.video_count,
                s.unique_channel_count,
                s.dominant_channel_title,
                s.total_duration_minutes,
                COALESCE(rt.parent_topic, 'General / Mixed') AS dominant_parent_topic,
                COALESCE(rt.topic_video_count, 0) AS dominant_topic_video_count
            FROM selected_sessions s
            LEFT JOIN ranked_topics rt
                ON rt.session_id = s.session_id
               AND rt.rn = 1
            ORDER BY s.session_start ASC
        """.replace("__TOPIC_EXPRESSION__", topicExpression);

        String topicBreakdownSql = """
            WITH selected_sessions AS (
                SELECT session_id
                FROM profile_watch_sessions
                WHERE profile_id = ?
                ORDER BY session_start DESC
                LIMIT ?
            ),
            session_event_topics AS (
                SELECT
                    a.session_id,
                    __TOPIC_EXPRESSION__ AS parent_topic
                FROM watch_event_session_assignments a
                JOIN raw_watch_events r
                    ON r.event_id = a.event_id
                LEFT JOIN youtube_videos y
                    ON y.video_id = r.video_id
                LEFT JOIN video_cluster_assignments vca
                    ON vca.video_id = r.video_id
                LEFT JOIN content_clusters c
                    ON c.cluster_id = vca.cluster_id
                WHERE a.profile_id = ?
                  AND a.session_id IN (
                      SELECT session_id
                      FROM selected_sessions
                  )
            )
            SELECT
                session_id,
                parent_topic,
                COUNT(*) AS video_count
            FROM session_event_topics
            GROUP BY session_id, parent_topic
            ORDER BY session_id, video_count DESC
        """.replace("__TOPIC_EXPRESSION__", topicExpression);

        String sessionEchoSql = """
            WITH selected_sessions AS (
                SELECT session_id
                FROM profile_watch_sessions
                WHERE profile_id = ?
                ORDER BY session_start DESC
                LIMIT ?
            ),
            session_cluster_counts AS (
                SELECT
                    a.session_id,
                    vca.cluster_id,
                    COALESCE(c.display_label, c.cluster_label, vca.cluster_id) AS cluster_label,
                    COUNT(*) AS video_count
                FROM watch_event_session_assignments a
                JOIN raw_watch_events r
                    ON r.event_id = a.event_id
                JOIN video_cluster_assignments vca
                    ON vca.video_id = r.video_id
                LEFT JOIN content_clusters c
                    ON c.cluster_id = vca.cluster_id
                WHERE a.profile_id = ?
                  AND a.session_id IN (
                      SELECT session_id
                      FROM selected_sessions
                  )
                GROUP BY
                    a.session_id,
                    vca.cluster_id,
                    COALESCE(c.display_label, c.cluster_label, vca.cluster_id)
            ),
            ranked_echo_scores AS (
                SELECT
                    e.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.profile_id, e.cluster_id
                        ORDER BY e.calculated_at DESC
                    ) AS rn
                FROM echo_chamber_scores e
                WHERE e.profile_id = ?
            ),
            joined_scores AS (
                SELECT
                    scc.session_id,
                    scc.cluster_id,
                    scc.cluster_label,
                    scc.video_count,
                    COALESCE(e.echo_score, 0.0) AS echo_score,
                    COALESCE(e.severity, 'info') AS severity
                FROM session_cluster_counts scc
                LEFT JOIN ranked_echo_scores e
                    ON e.cluster_id = scc.cluster_id
                   AND e.rn = 1
            ),
            session_echo AS (
                SELECT
                    session_id,
                    SUM(video_count * echo_score)
                        / NULLIF(SUM(video_count), 0) AS weighted_echo_score,
                    MAX(echo_score) AS max_echo_score,
                    SUM(
                        CASE
                            WHEN echo_score >= 25 THEN video_count
                            ELSE 0
                        END
                    ) AS high_echo_video_count
                FROM joined_scores
                GROUP BY session_id
            ),
            dominant_cluster AS (
                SELECT
                    session_id,
                    cluster_id,
                    cluster_label,
                    echo_score,
                    video_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY session_id
                        ORDER BY echo_score DESC, video_count DESC
                    ) AS rn
                FROM joined_scores
            )
            SELECT
                se.session_id,
                ROUND(
                    (
                        0.7 * COALESCE(se.weighted_echo_score, 0.0)
                        + 0.3 * COALESCE(se.max_echo_score, 0.0)
                    )::numeric,
                    2
                ) AS session_echo_score,
                COALESCE(se.high_echo_video_count, 0) AS high_echo_video_count,
                dc.cluster_id AS dominant_echo_cluster_id,
                dc.cluster_label AS dominant_echo_cluster_label
            FROM session_echo se
            LEFT JOIN dominant_cluster dc
                ON dc.session_id = se.session_id
               AND dc.rn = 1
        """;

        List<Map<String, Object>> topicRows = jdbcTemplate.queryForList(
            topicBreakdownSql,
            profileId,
            limit,
            profileId
        );

        List<Map<String, Object>> echoRows = jdbcTemplate.queryForList(
            sessionEchoSql,
            profileId,
            limit,
            profileId,
            profileId
        );

        Map<String, Map<String, Object>> echoBySession = new HashMap<>();

        for (Map<String, Object> row : echoRows) {
            echoBySession.put((String) row.get("session_id"), row);
        }

        Map<String, List<SessionSummaryGraphDto.TopicBreakdownDto>>
            topicsBySession = new HashMap<>();

        for (Map<String, Object> row : topicRows) {
            String sessionId = (String) row.get("session_id");
            String parentTopic = (String) row.get("parent_topic");
            Integer videoCount = ((Number) row.get("video_count")).intValue();

            topicsBySession
                .computeIfAbsent(sessionId, key -> new ArrayList<>())
                .add(new SessionSummaryGraphDto.TopicBreakdownDto(
                    parentTopic,
                    videoCount
                ));
        }

        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
            nodeSql,
            profileId,
            limit,
            profileId
        );

        List<SessionSummaryGraphDto.SessionNodeDto> nodes = new ArrayList<>();

        for (Map<String, Object> row : rows) {
            String sessionId = (String) row.get("session_id");

            Integer videoCount = ((Number) row.get("video_count")).intValue();
            Integer uniqueChannelCount =
                ((Number) row.get("unique_channel_count")).intValue();
            Integer dominantTopicVideoCount =
                ((Number) row.get("dominant_topic_video_count")).intValue();

            Double channelDiversity = videoCount == 0
                ? 0.0
                : uniqueChannelCount.doubleValue() / videoCount.doubleValue();

            Double topicConcentration = videoCount == 0
                ? 0.0
                : dominantTopicVideoCount.doubleValue() / videoCount.doubleValue();

            Map<String, Object> echoRow = echoBySession.get(sessionId);

            Double echoScore = 0.0;
            String echoSeverity = "info";
            String dominantEchoClusterId = null;
            String dominantEchoClusterLabel = null;
            Integer highEchoVideoCount = 0;

            if (echoRow != null) {
                Object scoreValue = echoRow.get("session_echo_score");

                if (scoreValue instanceof Number number) {
                    echoScore = number.doubleValue();
                }

                echoSeverity = echoSeverity(echoScore);
                dominantEchoClusterId =
                    (String) echoRow.get("dominant_echo_cluster_id");
                dominantEchoClusterLabel =
                    (String) echoRow.get("dominant_echo_cluster_label");

                Object highEchoValue = echoRow.get("high_echo_video_count");

                if (highEchoValue instanceof Number number) {
                    highEchoVideoCount = number.intValue();
                }
            }

            nodes.add(new SessionSummaryGraphDto.SessionNodeDto(
                sessionId,
                "Session " + row.get("session_index"),
                ((Number) row.get("session_index")).intValue(),
                toLocalDateTime(row.get("session_start")),
                toLocalDateTime(row.get("session_end")),
                videoCount,
                uniqueChannelCount,
                ((Number) row.get("total_duration_minutes")).intValue(),
                (String) row.get("dominant_channel_title"),
                (String) row.get("dominant_parent_topic"),
                dominantTopicVideoCount,
                channelDiversity,
                topicConcentration,

                echoScore,
                echoSeverity,
                dominantEchoClusterId,
                dominantEchoClusterLabel,
                highEchoVideoCount,

                topicsBySession.getOrDefault(sessionId, List.of())
            ));
        }

        List<SessionSummaryGraphDto.SessionEdgeDto> edges = new ArrayList<>();

        for (int i = 1; i < nodes.size(); i++) {
            edges.add(new SessionSummaryGraphDto.SessionEdgeDto(
                nodes.get(i - 1).id(),
                nodes.get(i).id(),
                "NEXT_SESSION"
            ));
        }

        return new SessionSummaryGraphDto(
            profileId,
            nodes,
            edges
        );
    }

    private LocalDateTime toLocalDateTime(Object value) {
        if (value == null) {
            return null;
        }

        if (value instanceof Timestamp timestamp) {
            return timestamp.toLocalDateTime();
        }

        if (value instanceof LocalDateTime localDateTime) {
            return localDateTime;
        }

        throw new IllegalArgumentException(
            "Unsupported timestamp value: " + value
        );
    }

    public EmbeddingProgressDto getEmbeddingProgress(String profileId) {
        String sql = """
            SELECT
                embedding_job_id,
                profile_id,
                status,
                total_videos,
                embedded_videos,
                failed_videos,
                CASE
                    WHEN total_videos = 0 THEN 0
                    ELSE ROUND((embedded_videos::numeric / total_videos::numeric) * 100, 2)
                END AS progress_percent
            FROM embedding_jobs
            WHERE profile_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """;
    
        List<EmbeddingProgressDto> rows = jdbcTemplate.query(
            sql,
            (rs, rowNum) -> new EmbeddingProgressDto(
                rs.getObject("embedding_job_id", java.util.UUID.class),
                rs.getString("profile_id"),
                rs.getString("status"),
                rs.getInt("total_videos"),
                rs.getInt("embedded_videos"),
                rs.getInt("failed_videos"),
                rs.getDouble("progress_percent")
            ),
            profileId
        );
    
        if (rows.isEmpty()) {
            return new EmbeddingProgressDto(
                null,
                profileId,
                "NOT_STARTED",
                0,
                0,
                0,
                0.0
            );
        }
    
        return rows.get(0);
    }
    
    public java.util.UUID createEmbeddingJob(String profileId, int batchSize) {
        String sql = """
            INSERT INTO embedding_jobs (
                profile_id,
                status,
                total_videos,
                embedded_videos,
                failed_videos,
                batch_size,
                created_at,
                updated_at
            )
            VALUES (
                ?,
                'PENDING',
                (
                    SELECT COUNT(DISTINCT video_id)
                    FROM raw_watch_events
                    WHERE profile_id = ?
                      AND video_id IS NOT NULL
                ),
                0,
                0,
                ?,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            RETURNING embedding_job_id
            """;
    
        return jdbcTemplate.queryForObject(
            sql,
            java.util.UUID.class,
            profileId,
            profileId,
            batchSize
        );
    }

    public boolean hasActiveEmbeddingJob(String profileId) {
        String sql = """
            SELECT COUNT(*)
            FROM embedding_jobs
            WHERE profile_id = ?
              AND status IN ('PENDING', 'RUNNING')
            """;
    
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class, profileId);
    
        return count != null && count > 0;
    }

    public void updateEmbeddingJobStatus(
        java.util.UUID embeddingJobId,
        String status,
        String errorMessage
    ) {
        String sql = """
            UPDATE embedding_jobs
            SET status = ?,
                error_message = ?,
                completed_at = CASE
                    WHEN ? = 'COMPLETED' THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE embedding_job_id = ?
            """;
    
        jdbcTemplate.update(
            sql,
            status,
            errorMessage,
            status,
            embeddingJobId
        );
    }

    private String echoSeverity(double score) {
        if (score >= 70) {
            return "high";
        }

        if (score >= 45) {
            return "medium";
        }

        if (score >= 25) {
            return "low";
        }

        return "info";
    }

}