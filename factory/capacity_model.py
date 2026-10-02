# factory/capacity_model.py  —  run:  python3 factory/capacity_model.py
# Cost + capacity calculator. Reads config/capacity.json (change assumptions in ONE place, rerun).
# The thesis is one number: positive replies per 100 delivered leads. This model estimates SPEND;
# replies-per-100 is measured from engagement_events once leads are flowing.
# NOTE: reconstructed from the dream-team summary's cited figures; swap in the real capacity.yaml when provided.
import json, os

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "capacity.json")


def _cfg():
    with open(CFG) as f:
        return json.load(f)


def _reuse(clients, table):
    pts = sorted((int(k), v) for k, v in table.items())
    if clients <= pts[0][0]:
        return pts[0][1]
    if clients >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= clients <= x1:
            return y0 + (y1 - y0) * (clients - x0) / (x1 - x0)
    return pts[-1][1]


def monthly(clients, leads_per_day=None):
    c = _cfg()
    lpd = leads_per_day or c["leads_per_client_per_day"]
    ready = clients * lpd * c["days_per_month"]
    gross_per_lead = sum(c["cost_per_ready_lead_usd"].values())
    reuse = _reuse(clients, c["dedup_reuse_rate"])
    eff_per_lead = gross_per_lead * (1 - reuse)
    total = ready * eff_per_lead
    offset = c["free_tier_offset_small_scale_usd_per_month"] if clients <= 10 else 0
    return {
        "clients": clients, "leads_per_client_per_day": lpd, "ready_leads_per_month": ready,
        "gross_cost_per_lead": round(gross_per_lead, 4), "dedup_reuse": round(reuse, 2),
        "effective_cost_per_lead": round(eff_per_lead, 4),
        "paid_rate_total_usd": round(total, 0), "paid_rate_per_client_usd": round(total / clients, 1),
        "with_free_tiers_total_usd": round(max(0, total - offset), 0),
    }


def table(counts=(10, 100, 1000), leads_per_day=None):
    c = _cfg()
    lpd = leads_per_day or c["leads_per_client_per_day"]
    print("Capacity model  (%d ready leads/client/day, %d days/mo)\n" % (lpd, c["days_per_month"]))
    hdr = "%-9s %-16s %-14s %-16s %-14s" % ("clients", "ready leads/mo", "per client", "per month (paid)", "reuse")
    print(hdr); print("-" * len(hdr))
    for n in counts:
        r = monthly(n, lpd)
        print("%-9d %-16d $%-13.0f $%-15.0f %-14s" % (
            r["clients"], r["ready_leads_per_month"], r["paid_rate_per_client_usd"],
            r["paid_rate_total_usd"], ("%d%%" % round(r["dedup_reuse"] * 100))))
    print("\nAt 10 clients, free tiers make it roughly $%d-250/mo real. Starting at 10 leads/day instead of %d cuts it further."
          % (monthly(10, lpd)["with_free_tiers_total_usd"], lpd))


if __name__ == "__main__":
    table()
