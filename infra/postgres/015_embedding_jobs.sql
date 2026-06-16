CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS embedding_jobs (
    embedding_job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    total_videos INTEGER NOT NULL DEFAULT 0,
    embedded_videos INTEGER NOT NULL DEFAULT 0,
    failed_videos INTEGER NOT NULL DEFAULT 0,
    batch_size INTEGER NOT NULL DEFAULT 64,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_embedding_jobs_profile_id
ON embedding_jobs(profile_id);

CREATE INDEX IF NOT EXISTS idx_embedding_jobs_status
ON embedding_jobs(status);

CREATE TABLE IF NOT EXISTS profile_video_embedding_status (
    profile_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY(profile_id, video_id)
);

CREATE INDEX IF NOT EXISTS idx_profile_video_embedding_status_profile
ON profile_video_embedding_status(profile_id);

CREATE INDEX IF NOT EXISTS idx_profile_video_embedding_status_status
ON profile_video_embedding_status(status);