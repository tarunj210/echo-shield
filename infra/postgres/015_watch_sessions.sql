CREATE TABLE IF NOT EXISTS profile_watch_sessions (
    session_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    session_index INTEGER NOT NULL,
    session_start TIMESTAMP NOT NULL,
    session_end TIMESTAMP NOT NULL,
    video_count INTEGER NOT NULL,
    unique_channel_count INTEGER NOT NULL,
    dominant_channel_title TEXT,
    total_duration_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_watch_session_profile
        FOREIGN KEY(profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watch_event_session_assignments (
    event_id UUID PRIMARY KEY,
    profile_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    sequence_in_session INTEGER NOT NULL,
    minutes_since_previous INTEGER,

    CONSTRAINT fk_event_session_event
        FOREIGN KEY(event_id)
        REFERENCES raw_watch_events(event_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_event_session_session
        FOREIGN KEY(session_id)
        REFERENCES profile_watch_sessions(session_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_watch_sessions_profile_id
ON profile_watch_sessions(profile_id);

CREATE INDEX IF NOT EXISTS idx_watch_sessions_start
ON profile_watch_sessions(session_start);

CREATE INDEX IF NOT EXISTS idx_event_session_session_id
ON watch_event_session_assignments(session_id);