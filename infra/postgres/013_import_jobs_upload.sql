CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS user_id TEXT;

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default_tenant';

CREATE TABLE IF NOT EXISTS import_jobs (
    import_job_id UUID PRIMARY KEY,
    profile_id TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    original_filename TEXT,
    stored_file_path TEXT,
    total_events INTEGER DEFAULT 0,
    inserted_events INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    CONSTRAINT fk_import_profile
        FOREIGN KEY(profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_import_jobs_profile_id
ON import_jobs(profile_id);

CREATE INDEX IF NOT EXISTS idx_import_jobs_status
ON import_jobs(status);