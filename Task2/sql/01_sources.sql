-- Local demonstration sources: separate CRM and telemetry schemas.
-- These are synthetic data, never real medical records.
CREATE SCHEMA IF NOT EXISTS crm;
CREATE SCHEMA IF NOT EXISTS telemetry;

CREATE TABLE IF NOT EXISTS crm.patients (
    id BIGINT PRIMARY KEY,
    issuer TEXT NOT NULL,
    oidc_sub TEXT NOT NULL,
    full_name TEXT NOT NULL,
    UNIQUE (issuer, oidc_sub)
);
CREATE TABLE IF NOT EXISTS crm.prostheses (
    id TEXT PRIMARY KEY,
    patient_id BIGINT NOT NULL REFERENCES crm.patients(id),
    active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS telemetry.samples (
    id BIGSERIAL PRIMARY KEY,
    prosthesis_id TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL CHECK (latency_ms >= 0),
    battery_pct DOUBLE PRECISION NOT NULL CHECK (battery_pct BETWEEN 0 AND 100)
);
CREATE INDEX IF NOT EXISTS ix_samples_day_device ON telemetry.samples(occurred_at, prosthesis_id);

INSERT INTO crm.patients (id,issuer,oidc_sub,full_name) VALUES
(1,'http://localhost:8080/realms/reports-realm','11111111-1111-4111-8111-111111111111','Demo User 1'),
(2,'http://localhost:8080/realms/reports-realm','22222222-2222-4222-8222-222222222222','Demo User 2')
ON CONFLICT (id) DO NOTHING;
INSERT INTO crm.prostheses (id,patient_id,active) VALUES
('p-100',1,TRUE),('p-101',1,TRUE),('p-200',2,TRUE)
ON CONFLICT (id) DO NOTHING;

-- Yesterday UTC: data becomes reportable after the corresponding DAG run.
INSERT INTO telemetry.samples (prosthesis_id,occurred_at,latency_ms,battery_pct)
SELECT sample.prosthesis_id,
       (date_trunc('day', now() AT TIME ZONE 'UTC') - INTERVAL '1 day'
          + sample.hh * INTERVAL '1 hour') AT TIME ZONE 'UTC',
       sample.latency_ms, sample.battery_pct
FROM (VALUES
 ('p-100',9,72.0,84.0),('p-100',10,81.0,76.0),
 ('p-101',11,91.0,64.0),('p-101',12,88.0,58.0),
 ('p-200',9,63.0,89.0),('p-200',10,68.0,83.0)
) sample(prosthesis_id,hh,latency_ms,battery_pct);
