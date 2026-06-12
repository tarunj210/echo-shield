ALTER TABLE content_clusters
ADD COLUMN IF NOT EXISTS keybert_keywords TEXT;

ALTER TABLE content_clusters
ADD COLUMN IF NOT EXISTS labelling_method TEXT;