# factory/packages/budget.py
# Treasury (ENRICHMENT_MASTER_PLAN §D8). Every PAID provider call goes through can_spend() before
# spending (free adapters, est $0, only log); every cost is logged to cost_ledger. Phase-1 version:
# kill switch + global monthly cap + per-provider monthly cap (from provider_accounts). Per-call price
# estimates live in config/prices.json (read via price()/prices()). Plan-level per-client budgets and
# the full acquire/settle allocator (TREASURY.md) are a later phase.
import os, json, datetime, threading
from urllib.parse import quote
from factory.packages import db


def _ts(iso):
    return quote(iso, safe="")  # encode '+' in the tz offset so PostgREST doesn't read it as a space


# RESERVED SLICES (operator, 2026-10-08): carve part of the daily global cap for ONE consumer so upstream steps
# can't eat the whole budget before it runs. The miner runs LAST among paid consumers, so without this a heavy
# drain/micro-route night would leave it $0 and it would silently produce 0. reserve("miner", 1.5) => upstream is
# limited to (cap - 1.5); the miner itself (when its pool is active) sees the full cap, so >=1.5 is always free for it.
# _ACTIVE is thread-local: drain's worker threads never activate a pool (they're "upstream"); the miner activates on
# its own single thread. NEVER raises; no cap is ever RAISED by this, only redistributed.
_ACTIVE = threading.local()
_RESERVED = {}  # pool_tag -> reserved usd


def reserve(tag, usd):
    _RESERVED[tag] = float(usd or 0)


def activate_pool(tag):
    _ACTIVE.pool = tag


def deactivate_pool():
    _ACTIVE.pool = None


def _active_pool():
    return getattr(_ACTIVE, "pool", None)


def spent_today():
    """Cumulative USD spent since 00:00 UTC today (the per-night window). Public read for the run's spend trace."""
    return _spent(since=_day_start_iso())


def daily_cap():
    return float(_cfg().get("daily_global_spend_cap_usd") or 0)

_CFG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "budgets.json")


def _cfg():
    with open(_CFG_PATH) as f:
        return json.load(f)


_PRICES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "prices.json")
_PRICES_CACHE = None


def prices():
    """Per-call cost estimates from config/prices.json (cached). Source of truth for provider adapters."""
    global _PRICES_CACHE
    if _PRICES_CACHE is None:
        with open(_PRICES_PATH) as f:
            _PRICES_CACHE = json.load(f)
    return _PRICES_CACHE


def price(key, default=0.0):
    v = prices().get(key, default)
    return float(v) if isinstance(v, (int, float)) else default


def _month_start_iso():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


def _day_start_iso():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _spent(provider=None, client_id=None, since=None):
    q = "select=usd_cost&created_at=gte.%s" % _ts(since or _month_start_iso())
    if provider:
        q += "&provider=eq.%s" % provider
    if client_id:
        q += "&client_id=eq.%s" % client_id
    rows = db.select("cost_ledger", q)
    return sum(float(r.get("usd_cost") or 0) for r in rows)


def can_spend(client_id, provider, est_usd):
    """Return (ok: bool, reason: str). A cap of 0/None = no limit set."""
    cfg = _cfg()
    if cfg.get("kill_switch_paid_spend"):
        return (False, "kill switch on")
    est = float(est_usd or 0)
    dcap = float(cfg.get("daily_global_spend_cap_usd") or 0)   # per-NIGHT ceiling: no single run/night can burst
    if dcap:
        active = _active_pool()
        total_reserved = sum(_RESERVED.values())
        # The active reserved consumer (miner) sees the FULL cap; everyone else (upstream) is capped at (cap - reserved)
        # so the reserved slice is always free when the consumer runs. No cap is raised — only redistributed.
        eff = dcap if (active and active in _RESERVED) else max(0.0, dcap - total_reserved)
        if _spent(since=_day_start_iso()) + est > eff:
            return (False, "global daily cap $%.2f reached (effective $%.2f for pool=%s)" % (dcap, eff, active or "upstream"))
    gcap = float(cfg.get("monthly_global_spend_cap_usd") or 0)
    if gcap and _spent() + est > gcap:
        return (False, "global monthly cap $%.2f reached" % gcap)
    if client_id:  # per-client cap from clients.icp_config.spend_cap_usd (0/absent = no limit)
        crow = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
        cicp = (crow[0].get("icp_config") or {}) if crow else {}
        # FD commercial/engagement gate: never spend on a paused client (idle non-paying demo). Door stays open
        # — the client is kept, FD just stops burning scarce credits on someone not working the leads.
        if (cicp.get("spend_policy") or "").lower() == "paused" and (cicp.get("commercial_status") or "").lower() != "paying":
            return (False, "client %s spend paused (idle/non-paying demo — FD stop)" % client_id)
        ccap = float((cicp.get("spend_cap_usd")) or 0)
        if ccap and _spent(client_id=client_id) + est > ccap:
            return (False, "client %s cap $%.2f reached" % (client_id, ccap))
    pa = db.select("provider_accounts", "provider=eq.%s&select=credits_remaining,monthly_cap_usd" % provider)
    if pa:
        cap = pa[0].get("monthly_cap_usd")
        if cap and _spent(provider=provider) + est > float(cap):
            return (False, "%s monthly cap $%.2f reached" % (provider, float(cap)))
        bal = pa[0].get("credits_remaining")
        if bal is not None and float(bal) <= 0:
            return (False, "%s out of credits" % provider)
    return (True, "ok")


def log_cost(provider, usd, client_id=None, company_id=None, job_type=None, credits=0, estimated=True):
    db.insert("cost_ledger", {
        "provider": provider, "client_id": client_id, "company_id": company_id,
        "job_type": job_type, "credits_used": credits, "usd_cost": usd, "estimated": estimated,
    }, returning=False)


def forecast(provider):
    """7-day burn rate -> days of runway. Alerts if runway < forecast_window_days (buy credits by then)."""
    cfg = _cfg()
    window = int(cfg.get("forecast_window_days") or 10)
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).isoformat()
    rows = db.select("cost_ledger", "provider=eq.%s&created_at=gte.%s&select=usd_cost" % (provider, _ts(since)))
    spent7 = sum(float(r.get("usd_cost") or 0) for r in rows)
    avg_daily = spent7 / 7.0
    pa = db.select("provider_accounts", "provider=eq.%s&select=credits_remaining,monthly_cap_usd" % provider)
    balance = None
    if pa:
        if pa[0].get("credits_remaining") is not None:
            balance = float(pa[0]["credits_remaining"])
        elif pa[0].get("monthly_cap_usd") is not None:
            balance = max(0.0, float(pa[0]["monthly_cap_usd"]) - _spent(provider=provider))
    days_left = (balance / avg_daily) if (balance is not None and avg_daily > 0) else None
    alert = days_left is not None and days_left < window
    if alert:
        try:
            from factory.packages import notify
            notify.notify("treasury forecast: %s runway %.1fd" % (provider, days_left),
                          "Buy more %s credits within %d days (balance $%.2f, ~$%.4f/day)." % (provider, window, balance or 0, avg_daily))
        except Exception:
            pass
    return {"provider": provider, "spent_7d": round(spent7, 4), "avg_daily": round(avg_daily, 4),
            "balance_usd": balance, "days_runway": (round(days_left, 1) if days_left is not None else None),
            "alert": alert, "message": ("Buy more %s credits within %d days" % (provider, window)) if alert else "ok"}
