from datetime import date

import pandas as pd

from pipeline import fetch
from pipeline.fetch import fetch_night_calls, night_where


def test_where_covers_friday_evening_and_saturday_early_morning():
    w = night_where(date(2026, 9, 1), date(2026, 9, 30))
    assert "BROOKLYN" in w
    assert "date_extract_dow(incident_datetime)=5 AND date_extract_hh(incident_datetime)>=18" in w
    assert "date_extract_dow(incident_datetime)=6 AND date_extract_hh(incident_datetime)<6" in w


def test_where_includes_saturday_after_last_friday():
    # end date is a Friday; its after-midnight calls fall on the next day
    w = night_where(date(2026, 9, 1), date(2026, 9, 25))
    assert "'2026-09-27T00:00:00'" in w


class _Resp:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        pass

    def json(self):
        return self._rows


def test_fetch_pages_until_empty(tmp_path, monkeypatch):
    pages = [[{"incident_id": "1"}, {"incident_id": "2"}],
             [{"incident_id": "3"}, {"incident_id": "4"}], []]
    offsets = []

    def fake_get(url, params, timeout):
        offsets.append(params["$offset"])
        return _Resp(pages[len(offsets) - 1])

    monkeypatch.setattr(fetch.requests, "get", fake_get)
    monkeypatch.setattr(fetch, "PAGE_SIZE", 2)
    out = fetch_night_calls(date(2026, 9, 1), date(2026, 9, 30), tmp_path / "r.parquet")
    assert len(pd.read_parquet(out)) == 4
    assert offsets == [0, 2, 4]
