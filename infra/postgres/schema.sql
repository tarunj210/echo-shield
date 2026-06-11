CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS profiles (
    profile_id TEXT PRIMARY KEY,
    display_name TEXT,
    profile_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_watch_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    watched_at TIMESTAMP NOT NULL,
    source TEXT NOT NULL,
    raw_title TEXT,
    raw_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_profile
        FOREIGN KEY(profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_raw_watch_events_profile_id
ON raw_watch_events(profile_id);

CREATE INDEX IF NOT EXISTS idx_raw_watch_events_video_id
ON raw_watch_events(video_id);

CREATE INDEX IF NOT EXISTS idx_raw_watch_events_watched_at
ON raw_watch_events(watched_at);