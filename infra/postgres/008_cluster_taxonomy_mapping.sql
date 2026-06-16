CREATE TABLE IF NOT EXISTS cluster_taxonomy_labels (
    cluster_id TEXT PRIMARY KEY,
    inferred_topic TEXT,
    inferred_risk_category TEXT,
    risk_score DOUBLE PRECISION,
    confidence DOUBLE PRECISION,
    explanation TEXT,
    model_version TEXT,
    labelled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_cluster_taxonomy_cluster
        FOREIGN KEY(cluster_id)
        REFERENCES content_clusters(cluster_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cluster_taxonomy_risk_category
ON cluster_taxonomy_labels(inferred_risk_category);

CREATE INDEX IF NOT EXISTS idx_cluster_taxonomy_risk_score
ON cluster_taxonomy_labels(risk_score);