# factory/workers/seed_import.py
# Item 6: operator insurance leads. The operator enriches a few companies by hand (separate chat, web tools)
# and drops a CSV at seeds/<client>.csv. The nightly run picks it up and pushes each row through the NORMAL
# chain: it writes facts (enrichment_findings, source_type=operator_seed, evidence_url kept, first_party),
# upserts the company + contact, and creates a DISCOVERED client_lead. From there the pipeline treats it like
# any other lead: Gate A corroboration, Gate B if report-bound, gates, READY. Nothing from the seed skips a
# gate. Each seeded field is tagged with the pivot that WOULD have found it (pivot_name): that is the recipe
# Gate A learns from. Idempotent: a row already seeded (same company+email) is skipped.
import os, csv, glob, datetime
from factory.packages import db

SEEDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "seeds")

# which pivot(s) would have produced each field for free, if the operator had not supplied it. The recipe.
WOULD_FIND = {
    "name":      "pivot_1_site_team | pivot_20_name_search | pivot_11_review_reply",
    "role":      "pivot_1_site | pivot_23_linkedin_snippet",
    "email":     "pivot_1_site | pivot_8_pattern_verify | pivot_22_email_search",
    "phone":     "pivot_1_site | pivot_11_places_details",
    "instagram": "pivot_1_site | pivot_9_ig_business_discovery",
    "linkedin":  "pivot_20_name_search | pivot_23_linkedin_snippet",
    "website":   "pivot_1_discovery",
    # evidence/metadata columns (2026-10-04): captured as facts so the gates + review can use them.
    "channel_type":     "operator_seed_evidence",
    "location_evidence": "pivot_11_places_details | operator_seed_evidence",
    "headcount_basis":   "pivot_17_linkedin_size | operator_seed_evidence",
}

# columns written as one enrichment_findings fact each (source_type=operator_seed)
SEED_FIELDS = ("name", "role", "email", "phone", "instagram", "linkedin", "website",
               "channel_type", "location_evidence", "headcount_basis")


def _domain(website):
    if not website:
        return None
    return website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].strip().lower() or None


def _person_key(name, company):
    return ("%s|%s" % ((name or "").strip().lower(), (company or "").strip().lower()))[:200]


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _upsert_company(name, website):
    dom = _domain(website)
    key = dom or (name or "").strip().lower()
    if not key:
        return None
    from urllib.parse import quote
    ex = db.select("companies", "dedupe_key=eq.%s&select=id" % quote(key, safe=""))
    if ex:
        return ex[0]["id"]
    return db.insert("companies", {"dedupe_key": key, "name": name, "website": website, "domain": dom}, returning=True)[0]["id"]


def _upsert_contact(company_id, row):
    email = (row.get("email") or "").strip().lower()
    ex = db.select("contacts", "company_id=eq.%s&email=eq.%s&select=id" % (company_id, email)) if email else []
    body = {"company_id": company_id, "full_name": row.get("name"), "title": row.get("role"),
            "email": row.get("email"), "email_status": "found", "email_source": "operator_seed",
            "phone": row.get("phone"), "instagram": row.get("instagram"), "linkedin_url": row.get("linkedin"),
            "is_decision_maker": True}
    if ex:
        db.update("contacts", "id=eq.%s" % ex[0]["id"], {k: v for k, v in body.items() if v})
        return ex[0]["id"]
    return db.insert("contacts", body, returning=True)[0]["id"]


def _already_seeded(company_id, email):
    q = "company_id=eq.%s&source_type=eq.operator_seed&select=id&limit=1" % company_id
    return bool(db.select("enrichment_findings", q))


def import_seeds():
    out = {"files": 0, "rows": 0, "imported": 0, "skipped_existing": 0, "by_client": {}}
    for path in sorted(glob.glob(os.path.join(SEEDS_DIR, "*.csv"))):
        client_id = os.path.splitext(os.path.basename(path))[0]
        out["files"] += 1
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
                if not (row.get("company") or row.get("website")):
                    continue
                out["rows"] += 1
                company_id = _upsert_company(row.get("company"), row.get("website"))
                if not company_id:
                    continue
                if _already_seeded(company_id, row.get("email")):
                    out["skipped_existing"] += 1
                    continue
                contact_id = _upsert_contact(company_id, row)
                pkey = _person_key(row.get("name"), row.get("company"))
                evid = [u.strip() for u in (row.get("evidence_urls") or "").replace(";", ",").split(",") if u.strip()]
                # one fact per supplied field, tagged with the pivot that would have found it (the recipe)
                for field in SEED_FIELDS:
                    val = row.get(field)
                    if not val:
                        continue
                    db.insert("enrichment_findings", {
                        "company_id": company_id, "field": field, "value": val, "source": "operator_seed",
                        "source_type": "operator_seed", "pivot_name": WOULD_FIND.get(field), "first_party": True,
                        "person_key": pkey, "confidence": 1.0, "evidence_url": (evid[0] if evid else None),
                    }, returning=False)
                # enters the NORMAL chain at DISCOVERED (tick -> enrich -> Gate A -> verify -> gates). No gate skipped.
                ex = db.select("client_leads", "client_id=eq.%s&company_id=eq.%s&select=id" % (client_id, company_id))
                if not ex:
                    db.insert("client_leads", {"client_id": client_id, "company_id": company_id,
                                               "contact_id": contact_id, "state": "DISCOVERED",
                                               "source": "operator_seed", "score": 0}, returning=False)
                out["imported"] += 1
                out["by_client"][client_id] = out["by_client"].get(client_id, 0) + 1
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(import_seeds(), indent=2))
