CREATE TABLE IF NOT EXISTS youtube_videos (
    video_id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    channel_id TEXT,
    channel_title TEXT,
    published_at TIMESTAMP,
    tags TEXT,
    category_id TEXT,
    duration TEXT,
    view_count BIGINT,
    like_count BIGINT,
    comment_count BIGINT,
    topic_categories TEXT,
    thumbnail_url TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_youtube_videos_channel_id
ON youtube_videos(channel_id);

CREATE INDEX IF NOT EXISTS idx_youtube_videos_category_id
ON youtube_videos(category_id);