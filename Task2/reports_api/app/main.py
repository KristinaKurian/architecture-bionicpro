"""Reports API: precomputed ClickHouse mart, no client-supplied user identity."""
import csv
from datetime import date, timedelta, datetime, timezone
from io import StringIO
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .auth import router as auth_router, get_principal
from .storage import (
    get_crm_conn, get_clickhouse, resolve_patient_and_prostheses,
    get_processed_days, get_report_rows,
)

app = FastAPI(title="BionicPRO Reports API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.include_router(auth_router)

@app.get("/health")
def health():
    return {"status": "ok"}


def report_content(principal, crm, ch, start: date, end: date, prosthesis_id: str | None):
    if end < start or end > datetime.now(timezone.utc).date() or (end - start).days > 30:
        raise HTTPException(422, "Choose a valid period of at most 31 days, not in the future")
    patient_id, owned_ids = resolve_patient_and_prostheses(
        crm, principal["iss"], principal["sub"]
    )
    if patient_id is None:
        raise HTTPException(403, "No patient record for this account")
    if prosthesis_id is not None and prosthesis_id not in owned_ids:
        raise HTTPException(403, "This prosthesis does not belong to the patient")
    # Check EVERY requested day, not just max(date), otherwise gaps leak incomplete reports.
    available = get_processed_days(ch, start, end)
    days = {start + timedelta(days=d) for d in range((end - start).days + 1)}
    if not days.issubset(available):
        raise HTTPException(409, "Requested period is not fully processed by Airflow")
    data = get_report_rows(ch, patient_id, start, end)
    selected = {prosthesis_id} if prosthesis_id else owned_ids
    return [row for row in data if row[1] in selected]

@app.get("/reports")
def get_reports(
    from_date: Annotated[date, Query(description="First UTC day to include")],
    to_date: Annotated[date, Query(description="Last UTC day to include")],
    principal: dict = Depends(get_principal),
    prosthesis_id: str | None = None,
):
    crm = get_crm_conn()
    ch = get_clickhouse()
    try:
        rows = report_content(principal, crm, ch, from_date, to_date, prosthesis_id)
    finally:
        crm.close()
        ch.close()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["report_date", "prosthesis_id", "sample_count", "avg_latency_ms",
                     "min_battery_pct", "max_battery_pct"])
    for dt, device, count, avg, battery_min, battery_max in rows:
        writer.writerow([dt.isoformat(), device, count, avg, battery_min, battery_max])
    return Response(
        output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="prosthesis-report.csv"',
                 "Cache-Control": "private, no-store"},
    )
