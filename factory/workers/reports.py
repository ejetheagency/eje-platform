# factory/workers/reports.py
# Report worker (D9). Precomputes a per-client daily report of READY leads into the `reports` table.
# The web app ONLY reads this payload (no computation in the request path). Run on the scheduler's tick.
import datetime
from factory.packages import db


def _today():
    return datetime.date.today().isoformat()


def build(client_id, report_date=None):
    report_date = report_date or _today()
    leads = db.select("client_leads",
                      "client_id=eq.%s&state=eq.READY&select=id,company_id,contact_id,score&order=score.desc&limit=200" % client_id)
    items = []
    for cl in leads:
        co = (db.select("companies", "id=eq.%s&select=name,domain,website,instagram,brief,logo_url" % cl["company_id"]) or [{}])[0]
        ct = {}
        if cl.get("contact_id"):
            ct = (db.select("contacts", "id=eq.%s&select=full_name,title,email" % cl["contact_id"]) or [{}])[0]
        sigs = db.select("signals", "company_id=eq.%s&select=type,detail&limit=5" % cl["company_id"])
        items.append({
            "client_lead_id": cl["id"], "score": cl.get("score"),
            "company": co.get("name"), "domain": co.get("domain"), "logo_url": co.get("logo_url"),
            "brief": co.get("brief"), "instagram": co.get("instagram"),
            "decisor": ct.get("full_name"), "title": ct.get("title"), "email": ct.get("email"),
            "why_now": [s["type"] for s in sigs],
        })
    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "client_id": client_id, "report_date": report_date,
        "count": len(items),
        "stats": {"ready": len(items),
                  "with_email": sum(1 for i in items if i["email"]),
                  "with_signal": sum(1 for i in items if i["why_now"])},
        "leads": items,
    }
    # upsert (one report per client per day)
    db.delete("reports", "client_id=eq.%s&report_date=eq.%s" % (client_id, report_date))
    db.insert("reports", {"client_id": client_id, "report_date": report_date, "payload": payload}, returning=False)
    return {"client_id": client_id, "report_date": report_date, "count": len(items), "stats": payload["stats"]}


def build_all(report_date=None):
    clients = db.select("clients", "select=id")
    return [build(c["id"], report_date) for c in clients]


if __name__ == "__main__":
    import json
    print(json.dumps(build_all(), indent=2))
