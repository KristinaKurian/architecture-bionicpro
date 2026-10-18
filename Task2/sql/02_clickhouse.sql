CREATE DATABASE IF NOT EXISTS bionicpro;

CREATE TABLE IF NOT EXISTS bionicpro.user_prosthesis_reports (
    report_date Date,
    user_id UInt64,
    prosthesis_id String,
    sample_count UInt64,
    avg_latency_ms Nullable(Float64),
    min_battery_pct Nullable(Float64),
    max_battery_pct Nullable(Float64),
    processed_at DateTime64(3, 'UTC') DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(processed_at)
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, user_id, prosthesis_id);

CREATE TABLE IF NOT EXISTS bionicpro.etl_processed_days (
    report_date Date,
    loaded_rows UInt64,
    processed_at DateTime64(3, 'UTC') DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(processed_at)
ORDER BY report_date;
