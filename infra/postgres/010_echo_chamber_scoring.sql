CREATE TABLE IF NOT EXISTS profile_cluster_exposure_windows (
    profile_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    window_days INTEGER NOT NULL,
    window_type TEXT NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    watch_count INTEGER NOT NULL,
    total_watch_count INTEGER NOT NULL,
    exposure_ratio DOUBLE PRECISION NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (profile_id, cluster_id, window_days, window_type),

    CONSTRAINT fk_exposure_window_profile
        FOREIGN KEY(profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_exposure_window_cluster
        FOREIGN KEY(cluster_id)
        REFERENCES content_clusters(cluster_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS echo_chamber_scores (
    profile_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    window_days INTEGER NOT NULL,

    current_watch_count INTEGER NOT NULL,
    current_total_watch_count INTEGER NOT NULL,
    current_exposure_ratio DOUBLE PRECISION NOT NULL,

    previous_exposure_ratio DOUBLE PRECISION NOT NULL,
    trend_delta DOUBLE PRECISION NOT NULL,

    inferred_risk_category TEXT,
    taxonomy_risk_score DOUBLE PRECISION,

    echo_score DOUBLE PRECISION NOT NULL,
    severity TEXT NOT NULL,
    explanation TEXT,
    model_version TEXT,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (profile_id, cluster_id, window_days),

    CONSTRAINT fk_echo_score_profile
        FOREIGN KEY(profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_echo_score_cluster
        FOREIGN KEY(cluster_id)
        REFERENCES content_clusters(cluster_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_exposure_windows_profile
ON profile_cluster_exposure_windows(profile_id);

CREATE INDEX IF NOT EXISTS idx_exposure_windows_cluster
ON profile_cluster_exposure_windows(cluster_id);

CREATE INDEX IF NOT EXISTS idx_echo_scores_profile
ON echo_chamber_scores(profile_id);

CREATE INDEX IF NOT EXISTS idx_echo_scores_score
ON echo_chamber_scores(echo_score);

CREATE INDEX IF NOT EXISTS idx_echo_scores_severity
ON echo_chamber_scores(severity);