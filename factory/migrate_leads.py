# factory/migrate_leads.py
# One-time backfill: the old flat `leads` table -> the new model.
#   - eje_productoras (the data-asset LIBRARY) -> global companies + contacts ONLY (the shared pool).
#   - real clients (eje, nanovideos, 2uplatam, somoshobby) -> companies (deduped, may reuse pool) + contacts + client_leads.
# The old `leads` table is NOT modified (read-only). Outreach history stays keyed by legacy_lead_id.
# Dry-run by default (writes NOTHING); pass --apply to write. Idempotent: dedupe_key reuse + client/company skip.
#   python3 -m factory.migrate_leads            # dry run
#   python3 -m factory.migrate_leads --apply    # execute
import sys, json, re
from factory.packages import db

DRY = "--apply" not in sys.argv
LIBRARY_CLIENTS = {"eje_productoras"}


def norm_domain(url):
    if not url:
        return None
    u = str(url).strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("/")[0].split("?")[0].strip()
    return u or None


def norm_name(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def ig_handle(ld):
    h = ld.get("instagramHandle") or ""
    if not h and ld.get("instagramUrl"):
        m = re.search(r"instagram\.com/([^/?]+)", str(ld["instagramUrl"]))
        h = m.group(1) if m else ""
    h = re.sub(r"[^a-z0-9_.]", "", str(h).lower().lstrip("@"))
    return h or None


def paged(table, cols):
    out, off = [], 0
    while True:
        page = db.select(table, "select=%s&order=id&limit=1000&offset=%d" % (cols, off))
        out += page
        if len(page) < 1000:
            return out
        off += 1000


def state_for(status):
    return "DISCARDED" if status == "skip" else "DELIVERED"


def main():
    leads = paged("leads", "id,company,contact_name,contact_email,contact_phone,country,industry,score,status,client_id,lead_data")
    print("fetched %d leads" % len(leads))

    comp_by_key = {}
    for c in paged("companies", "id,dedupe_key"):
        comp_by_key[c["dedupe_key"]] = c["id"]

    contact_cache = {}
    seen_client_company = set()
    st = {"companies_new": 0, "companies_reused": 0, "contacts_new": 0,
          "client_leads_new": 0, "client_leads_skipped": 0, "pool_only": 0}

    def get_company(ld, lead):
        dom = norm_domain(ld.get("website"))
        ig = ig_handle(ld)
        name = ld.get("companyName") or lead.get("company") or "Unknown"
        country = ld.get("country") or lead.get("country")
        if dom:
            key = dom
        elif ig:
            key = "ig:" + ig
        elif norm_name(name):
            key = "name:" + norm_name(name) + "|" + norm_name(country or "")
        else:
            key = "lead:" + lead["id"]
        if key in comp_by_key:
            st["companies_reused"] += 1
            return comp_by_key[key]
        row = {"dedupe_key": key, "domain": dom, "name": name, "country": country,
               "industry": ld.get("industry") or lead.get("industry"),
               "website": ld.get("website"), "instagram": ig,
               "linkedin": ld.get("apolloCompanyLinkedIn") or ld.get("contactLinkedIn"),
               "brief": ld.get("companyBrief") or ld.get("summary"),
               "logo_url": ld.get("logo")}
        cid = ("DRY-" + key) if DRY else db.insert("companies", row)[0]["id"]
        comp_by_key[key] = cid
        st["companies_new"] += 1
        if ld.get("logo") and not DRY:
            db.insert("assets", {"company_id": cid, "kind": "logo", "url": ld["logo"], "source": "migrated"}, returning=False)
        return cid

    def get_contact(cid, name, email, phone, title, dm=False):
        el = (email or "").lower().strip()
        ck = (cid, el)
        if el and ck in contact_cache:
            return contact_cache[ck]
        row = {"company_id": cid, "full_name": name,
               "first_name": (name.split(" ")[0] if name else None), "title": title,
               "is_decision_maker": dm, "email": email or None,
               "email_status": "verified" if email else "unknown", "phone": phone}
        if DRY:
            contact_id = "DRY"
        else:
            try:
                contact_id = db.insert("contacts", row)[0]["id"]
                st["contacts_new"] += 1
            except db.Conflict:
                # already exists (same company+email): reuse it, don't duplicate
                existing = db.select("contacts", "company_id=eq.%s&email=eq.%s&select=id" % (cid, el))
                contact_id = existing[0]["id"] if existing else None
        if DRY:
            st["contacts_new"] += 1
        if el and contact_id:
            contact_cache[ck] = contact_id
        return contact_id

    for lead in leads:
        ld = lead.get("lead_data") or {}
        cid = get_company(ld, lead)
        pname = ld.get("contactName") or lead.get("contact_name")
        pemail = ld.get("contactEmail") or lead.get("contact_email")
        primary = None
        if pname or pemail:
            primary = get_contact(cid, pname, pemail, ld.get("contactPhone") or lead.get("contact_phone"), ld.get("contactTitle"), dm=True)
        for ac in (ld.get("additionalContacts") or []):
            if isinstance(ac, dict) and (ac.get("name") or ac.get("email")):
                get_contact(cid, ac.get("name"), ac.get("email"), ac.get("phone"), ac.get("title"))

        if lead["client_id"] in LIBRARY_CLIENTS:
            st["pool_only"] += 1
            continue
        ck = (lead["client_id"], cid)
        if ck in seen_client_company:
            st["client_leads_skipped"] += 1
            continue
        seen_client_company.add(ck)
        cl = {"client_id": lead["client_id"], "company_id": cid,
              "contact_id": (None if DRY else primary),
              "state": state_for(lead.get("status")), "score": lead.get("score"),
              "source": ld.get("source") or ld.get("contactSource") or "migrated",
              "ready": bool(ld.get("readyToSend") or ld.get("approved")),
              "quality_flags": {"legacy_status": lead.get("status")}, "legacy_lead_id": lead["id"]}
        if not DRY:
            try:
                db.insert("client_leads", cl, returning=False)
            except Exception:
                st["client_leads_skipped"] += 1
                continue
        st["client_leads_new"] += 1

    print(json.dumps(st, indent=2))
    print("MODE:", "DRY-RUN (nothing written)" if DRY else "APPLIED")


if __name__ == "__main__":
    main()
