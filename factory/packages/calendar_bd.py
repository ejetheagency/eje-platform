# factory/packages/calendar_bd.py
# Per-client business-day calendar (operator 2026-10-08): a paying client never gets a report on a non-business day
# (weekend OR a public holiday in the client's country); the content delivers on the NEXT business day instead.
# Country holidays live in config/holidays.json; a client's country = clients.icp_config.geo. Used by release.py +
# reports.py. Weekends (Sat/Sun) are always non-business. Never raises; unknown country = weekends-only.
import os, json, datetime

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "holidays.json")
_CACHE = None


def _holidays():
    global _CACHE
    if _CACHE is None:
        try:
            with open(_PATH) as f:
                _CACHE = json.load(f)
        except Exception:
            _CACHE = {}
    return _CACHE


def holidays_for(country):
    return set(_holidays().get(country or "", []) or [])


def _as_date(d):
    return datetime.date.fromisoformat(d) if isinstance(d, str) else d


def is_business_day(d, country=None):
    d = _as_date(d)
    if d.weekday() >= 5:            # Saturday=5, Sunday=6
        return False
    return d.isoformat() not in holidays_for(country)


def next_business_day(d, country=None):
    d = _as_date(d)
    while not is_business_day(d, country):
        d += datetime.timedelta(days=1)
    return d


def business_days_from(d, n, country=None):
    """The next n business days at or after d (inclusive if d is one)."""
    out, cur = [], next_business_day(d, country)
    while len(out) < n:
        out.append(cur)
        cur = next_business_day(cur + datetime.timedelta(days=1), country)
    return out
