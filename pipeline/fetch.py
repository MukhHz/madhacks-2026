"""Download Friday-night (Fri 18:00 -> Sat 06:00) EMS incidents for the configured area.

Run: python -m pipeline.fetch 2024-01-01 2026-09-30 data/raw/fridays.parquet
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import CITY, RAW_COLUMNS

PAGE_SIZE = 50000


def night_where(start: date, end: date) -> str:
    """SoQL filter for Friday evenings plus the Saturday early mornings that belong to them."""
    lo = start.isoformat() + "T00:00:00"
    hi = (end + timedelta(days=2)).isoformat() + "T00:00:00"
    return (
        f"borough='{CITY['borough_filter']}' "
        f"AND incident_datetime >= '{lo}' AND incident_datetime < '{hi}' "
        "AND ((date_extract_dow(incident_datetime)=5 AND date_extract_hh(incident_datetime)>=18) "
        "OR (date_extract_dow(incident_datetime)=6 AND date_extract_hh(incident_datetime)<6))"
    )


def fetch_night_calls(start: date, end: date, out: Path) -> Path:
    rows: list[dict] = []
    offset = 0
    while True:
        params = {"$select": ",".join(RAW_COLUMNS), "$where": night_where(start, end),
                  "$order": "incident_id", "$limit": PAGE_SIZE, "$offset": offset}
        resp = requests.get(CITY["socrata_url"], params=params, timeout=120)
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break
        rows.extend(page)
        offset += PAGE_SIZE
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out)
    return out


if __name__ == "__main__":
    s, e, o = sys.argv[1:4]
    path = fetch_night_calls(date.fromisoformat(s), date.fromisoformat(e), Path(o))
    print(f"wrote {path}: {len(pd.read_parquet(path))} rows")
