CREATE TABLE IF NOT EXISTS validation_samples (
    sample_id TEXT PRIMARY KEY,
    source_dataset TEXT NOT NULL,
    split_name TEXT,
    source_label TEXT NOT NULL,
    expected_category TEXT NOT NULL,
    text TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS validation_predictions (
    sample_id TEXT PRIMARY KEY,
    expected_category TEXT NOT NULL,
    predicted_category TEXT NOT NULL,
    predicted_topic TEXT,
    confidence DOUBLE PRECISION,
    risk_score DOUBLE PRECISION,
    is_match BOOLEAN NOT NULL,
    model_version TEXT,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_validation_prediction_sample
        FOREIGN KEY(sample_id)
        REFERENCES validation_samples(sample_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_validation_samples_expected_category
ON validation_samples(expected_category);

CREATE INDEX IF NOT EXISTS idx_validation_samples_source_dataset
ON validation_samples(source_dataset);

CREATE INDEX IF NOT EXISTS idx_validation_predictions_predicted_category
ON validation_predictions(predicted_category);

CREATE INDEX IF NOT EXISTS idx_validation_predictions_is_match
ON validation_predictions(is_match);