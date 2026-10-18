"""BionicPRO ETL: CRM + telemetry database -> preaggregated ClickHouse mart.

Runs once per UTC day. XCom only transports an integer row count, never raw
medical data. Repeated runs replace the same business keys in ClickHouse.
"""
import os
from contextlib import closing
from datetime import date, datetime, timezone

import clickhouse_connect
import pendulum
import psycopg2
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context


def pg():
    return psycopg2.connect(os.environ["SOURCE_DATABASE_URL"])


def ch():
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
        username=os.getenv("CLICKHOUSE_USER", "reporter"),
        password=os.environ["CLICKHOUSE_PASSWORD"],
        database="bionicpro",
    )


def current_report_date() -> date:
    context = get_current_context()
    override = (context.get("dag_run").conf or {}).get("report_date") if context.get("dag_run") else None
    if override:
        return date.fromisoformat(override)
    return context["data_interval_start"].in_timezone("UTC").date()


def build_daily_rows(conn, day):
    """Combine CRM ownership with aggregated sensor readings for one UTC day."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, patient_id FROM crm.prostheses WHERE active=TRUE")
        ownership = dict(cur.fetchall())
        cur.execute("""
            SELECT prosthesis_id, COUNT(*)::bigint, AVG(latency_ms)::float8,
                   MIN(battery_pct)::float8, MAX(battery_pct)::float8
            FROM telemetry.samples
            WHERE occurred_at >= %s::date AND occurred_at < (%s::date + INTERVAL '1 day')
            GROUP BY prosthesis_id
        """, (day, day))
        aggregate = {row[0]: row[1:] for row in cur.fetchall()}
    rows = []
    for device, patient_id in sorted(ownership.items()):
        count, avg, minimum, maximum = aggregate.get(device, (0, None, None, None))
        rows.append([day, patient_id, device, count, avg, minimum, maximum])
    return rows


@dag(
    dag_id="bionicpro_reports_daily",
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["bionicpro", "reports", "etl"],
    default_args={"retries": 2},
)
def reports_pipeline():
    @task
    def load_daily_mart():
        day = current_report_date()
        with closing(pg()) as conn:
            rows = build_daily_rows(conn, day)
        client = ch()
        try:
            if rows:
                client.insert("user_prosthesis_reports", rows, column_names=[
                    "report_date", "user_id", "prosthesis_id", "sample_count",
                    "avg_latency_ms", "min_battery_pct", "max_battery_pct",
                ])
        finally:
            client.close()
        return {"day": day.isoformat(), "rows": len(rows)}

    @task
    def mark_day_complete(result):
        # Watermark is written only after the mart insert has succeeded.
        client = ch()
        try:
            client.insert("etl_processed_days", [[date.fromisoformat(result["day"]), result["rows"]]],
                          column_names=["report_date", "loaded_rows"])
        finally:
            client.close()

    mark_day_complete(load_daily_mart())


reports_pipeline()
