"""Storage adapters: CRM is the source of truth for ownership."""
import os
import psycopg2
import clickhouse_connect


def get_crm_conn():
    return psycopg2.connect(os.environ["SOURCE_DATABASE_URL"])


def get_clickhouse():
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_USER", "reporter"),
        password=os.environ["CLICKHOUSE_PASSWORD"],
        database="bionicpro",
    )


def resolve_patient_and_prostheses(conn, issuer: str, sub: str):
    """Never take patient ownership from request query arguments."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM crm.patients WHERE issuer=%s AND oidc_sub=%s", (issuer, sub))
        row = cur.fetchone()
        if row is None:
            return None, set()
        patient_id = int(row[0])
        cur.execute("SELECT id FROM crm.prostheses WHERE patient_id=%s AND active=TRUE", (patient_id,))
        return patient_id, {p[0] for p in cur.fetchall()}


def get_processed_days(ch, start, end):
    data = ch.query(
        "SELECT report_date FROM etl_processed_days FINAL "
        "WHERE report_date BETWEEN {start:Date} AND {end:Date}",
        parameters={"start": start, "end": end},
    )
    return {row[0] for row in data.result_rows}


def get_report_rows(ch, patient_id, start, end):
    data = ch.query(
        "SELECT report_date, prosthesis_id, sample_count, avg_latency_ms, "
        "min_battery_pct, max_battery_pct "
        "FROM user_prosthesis_reports FINAL "
        "WHERE user_id = {patient_id:UInt64} "
        "AND report_date BETWEEN {start:Date} AND {end:Date} "
        "ORDER BY report_date, prosthesis_id",
        parameters={"patient_id": patient_id, "start": start, "end": end},
    )
    return data.result_rows
