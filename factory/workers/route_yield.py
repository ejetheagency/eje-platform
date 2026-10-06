# factory/workers/route_yield.py
# BRICK 1 of THE NORTH (Innovations<->Miners loop): the route-yield READ layer over enrichment_findings.
# You cannot "repeat the high-yield routes" until you can SEE which route finds the valuable things — DECISORS
# and EMAILS — best, PER ICP, at what cost. This reads the 3.5k findings and ranks routes per client.
#
# Route key = pivot_name when present (the pivot that worked), else source (site_enrich/gemini/operator_seed/...).
# strategy_id is still empty (the `strategies` registry is the next brick); source+pivot_name are what we have now.
# Findings are company-keyed, so we attribute each to its client(s) via client_leads (company_id -> client_id).
from collections import defaultdict
from factory.packages import db

DECISOR_FIELDS = {"person_name", "name", "role"}   # the 30%-gate bottleneck: who is the decisor
EMAIL_FIELDS = {"email", "email_candidates"}        # the other wall: a reachable address


def _company_clients():
    m = defaultdict(set)
    for r in db.select_all("client_leads", "select=company_id,client_id"):
        if r.get("company_id"):
            m[r["company_id"]].add(r["client_id"])
    return m


def compute(client_id=None):
    cc = _company_clients()
    agg = {}  # (client, route) -> counters
    for f in db.select_all("enrichment_findings",
                           "select=company_id,field,source,pivot_name,cost_usd,verified_at"):
        clients = cc.get(f.get("company_id"), set())
        if client_id:
            clients = clients & {client_id}
        if not clients:
            continue
        route = f.get("pivot_name") or f.get("source") or "?"
        field = f.get("field")
        cost = float(f.get("cost_usd") or 0)
        for cl in clients:
            a = agg.setdefault((cl, route), {"findings": 0, "decisor": 0, "email": 0,
                                             "email_verified": 0, "cost": 0.0})
            a["findings"] += 1
            a["cost"] += cost
            if field in DECISOR_FIELDS:
                a["decisor"] += 1
            if field in EMAIL_FIELDS:
                a["email"] += 1
            if field == "email" and f.get("verified_at"):
                a["email_verified"] += 1
    return agg


def ranked(client_id, by="decisor", top=15):
    agg = compute(client_id=client_id)
    rows = [{"route": rt, **v} for (cl, rt), v in agg.items() if cl == client_id]
    rows.sort(key=lambda r: (r.get(by, 0), r["findings"]), reverse=True)
    return rows[:top]


def report(client_id):
    rows = ranked(client_id, by="decisor", top=20)
    tot_d = sum(r["decisor"] for r in rows)
    tot_e = sum(r["email"] for r in rows)
    print("== route yield for %s (ranked by DECISORs found) ==" % client_id)
    print("%-42s %8s %8s %8s %7s %8s" % ("route", "findings", "decisor", "email", "e_verif", "cost$"))
    for r in rows:
        print("%-42s %8d %8d %8d %7d %8.3f" % (
            r["route"][:42], r["findings"], r["decisor"], r["email"], r["email_verified"], r["cost"]))
    print("-- totals: decisor_finds=%d  email_finds=%d --" % (tot_d, tot_e))


if __name__ == "__main__":
    import sys
    report(sys.argv[1] if len(sys.argv) > 1 else "2uplatam")
