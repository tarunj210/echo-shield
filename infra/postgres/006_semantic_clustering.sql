CREATE TABLE IF NOT EXISTS video_embeddings (
    video_id TEXT PRIMARY KEY,
    embedding DOUBLE PRECISION[] NOT NULL,
    model_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_embedding_video
        FOREIGN KEY(video_id)
        REFERENCES youtube_videos(video_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS video_similarity_edges (
    source_video_id TEXT NOT NULL,
    target_video_id TEXT NOT NULL,
    similarity DOUBLE PRECISION NOT NULL,
    model_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (source_video_id, target_video_id),

    CONSTRAINT fk_similarity_source
        FOREIGN KEY(source_video_id)
        REFERENCES youtube_videos(video_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_similarity_target
        FOREIGN KEY(target_video_id)
        REFERENCES youtube_videos(video_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS content_clusters (
    cluster_id TEXT PRIMARY KEY,
    cluster_label TEXT,
    summary TEXT,
    top_terms TEXT,
    video_count INTEGER DEFAULT 0,
    model_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS video_cluster_assignments (
    video_id TEXT PRIMARY KEY,
    cluster_id TEXT NOT NULL,
    confidence DOUBLE PRECISION,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_video_cluster_video
        FOREIGN KEY(video_id)
        REFERENCES youtube_videos(video_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_video_cluster_cluster
        FOREIGN KEY(cluster_id)
        REFERENCES content_clusters(cluster_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_video_similarity_source
ON video_similarity_edges(source_video_id);

CREATE INDEX IF NOT EXISTS idx_video_similarity_target
ON video_similarity_edges(target_video_id);

CREATE INDEX IF NOT EXISTS idx_video_similarity_score
ON video_similarity_edges(similarity);

CREATE INDEX IF NOT EXISTS idx_video_cluster_assignments_cluster_id
ON video_cluster_assignments(cluster_id);