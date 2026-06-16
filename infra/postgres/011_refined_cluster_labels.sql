ALTER TABLE content_clusters
ADD COLUMN IF NOT EXISTS raw_cluster_label TEXT;

ALTER TABLE content_clusters
ADD COLUMN IF NOT EXISTS display_label TEXT;

ALTER TABLE content_clusters
ADD COLUMN IF NOT EXISTS parent_label TEXT;

ALTER TABLE content_clusters
ADD COLUMN IF NOT EXISTS parent_label_confidence DOUBLE PRECISION;

ALTER TABLE content_clusters
ADD COLUMN IF NOT EXISTS parent_label_margin DOUBLE PRECISION;

ALTER TABLE content_clusters
ADD COLUMN IF NOT EXISTS label_refinement_reason TEXT;

ALTER TABLE content_clusters
ADD COLUMN IF NOT EXISTS label_source TEXT;