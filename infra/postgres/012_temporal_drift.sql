CREATE TABLE IF NOT EXISTS profile_topic_exposure_timeseries (
    profile_id TEXT NOT NULL,
    parent_label TEXT NOT NULL,
    granularity TEXT NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    watch_count INTEGER NOT NULL,
    total_watch_count INTEGER NOT NULL,
    exposure_ratio DOUBLE PRECISION NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (profile_id, parent_label, granularity, window_start, window_end),

    CONSTRAINT fk_topic_timeseries_profile
        FOREIGN KEY(profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile_cluster_exposure_timeseries (
    profile_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    granularity TEXT NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    watch_count INTEGER NOT NULL,
    total_watch_count INTEGER NOT NULL,
    exposure_ratio DOUBLE PRECISION NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (profile_id, cluster_id, granularity, window_start, window_end),

    CONSTRAINT fk_cluster_timeseries_profile
        FOREIGN KEY(profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_cluster_timeseries_cluster
        FOREIGN KEY(cluster_id)
        REFERENCES content_clusters(cluster_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile_temporal_drift_signals (
    profile_id TEXT NOT NULL,
    granularity TEXT NOT NULL,
    previous_window_start TIMESTAMP NOT NULL,
    previous_window_end TIMESTAMP NOT NULL,
    current_window_start TIMESTAMP NOT NULL,
    current_window_end TIMESTAMP NOT NULL,

    dominant_topic_before TEXT,
    dominant_topic_after TEXT,

    topic_drift_score DOUBLE PRECISION NOT NULL,
    cluster_drift_score DOUBLE PRECISION NOT NULL,
    novelty_ratio DOUBLE PRECISION NOT NULL,
    risk_exposure_before DOUBLE PRECISION NOT NULL,
    risk_exposure_after DOUBLE PRECISION NOT NULL,
    risk_exposure_delta DOUBLE PRECISION NOT NULL,

    drift_score DOUBLE PRECISION NOT NULL,
    severity TEXT NOT NULL,
    explanation TEXT,
    model_version TEXT,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (profile_id, granularity, current_window_start, current_window_end),

    CONSTRAINT fk_temporal_drift_profile
        FOREIGN KEY(profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_topic_timeseries_profile_window
ON profile_topic_exposure_timeseries(profile_id, granularity, window_start, window_end);

CREATE INDEX IF NOT EXISTS idx_cluster_timeseries_profile_window
ON profile_cluster_exposure_timeseries(profile_id, granularity, window_start, window_end);

CREATE INDEX IF NOT EXISTS idx_temporal_drift_profile_score
ON profile_temporal_drift_signals(profile_id, drift_score);

CREATE INDEX IF NOT EXISTS idx_temporal_drift_severity
ON profile_temporal_drift_signals(severity);