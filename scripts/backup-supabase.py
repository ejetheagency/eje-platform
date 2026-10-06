#!/usr/bin/env python3
# scripts/backup-supabase.py
#
# PHASE 0 safety net: full logical backup of the Supabase project to timestamped JSON.
# Read-only (anon key). Paginates past the PostgREST 1000-row cap. One file per table
# plus a manifest with row counts. Restore = POST the rows back per table.
#
#   python3 scripts/backup-supabase.py            # snapshot -> backups/<UTC-stamp>/
#
# NOTE: backups/ is gitignored (client data + large). Keep snapshots somewhere durable
# for real disaster recovery; this gives an immediate local restore point.

import json, os, sys, urllib.request, datetime

SB = "https://ogdsuztzhmnnjolilsuo.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZHN1enR6aG1ubmpvbGlsc3VvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMDI0MDMsImV4cCI6MjA5MTc3ODQwM30.9iKhJJWd_zg6WfdxTR9ojK4DVLR3e-bLdPXY-0uDp7Q"
H = {"apikey": KEY, "Authorization": "Bearer " + KEY}
TABLES = ["leads", "messages_sent", "actions", "status_history", "notes",
          "tracked_leads", "tracked_lead_notes", "landing_events"]

def page_all(table):
    rows, off = [], 0
    while True:
        url = f"{SB}/rest/v1/{table}?select=*&limit=1000&offset={off}"
        try:
            chunk = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=H)))
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return None  # table absent / not exposed
            raise
        rows += chunk
        if len(chunk) < 1000:
            return rows
        off += 1000

def main():
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    root = os.path.join(os.path.dirname(__file__), "..", "backups", stamp)
    os.makedirs(root, exist_ok=True)
    manifest = {"taken_at_utc": stamp, "project": "ogdsuztzhmnnjolilsuo", "tables": {}}
    print("Supabase backup ->", os.path.relpath(root))
    for t in TABLES:
        rows = page_all(t)
        if rows is None:
            print(f"  {t:20} (absent, skipped)")
            continue
        json.dump(rows, open(os.path.join(root, t + ".json"), "w"), ensure_ascii=False)
        manifest["tables"][t] = len(rows)
        print(f"  {t:20} {len(rows):5} rows")
    json.dump(manifest, open(os.path.join(root, "_manifest.json"), "w"), indent=2)
    print("done. total tables:", len(manifest["tables"]))

if __name__ == "__main__":
    main()
