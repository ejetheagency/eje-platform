# EJE Platform, Staging Environment Setup

_Phase 0 step 3. Goal: a full copy of the app + a separate database, so nothing risky is ever tested in
production again. Everything below is done once. It needs YOUR Vercel + Supabase accounts, so it is a
guided checklist, not something the assistant can run headless._

## Why
The rebrand (Phase 2) and the auth/RLS work (Phase 1) both touch the live app and 1,394 real records.
Staging is the safety net that lets us build them boldly: break staging freely, promote to prod only when proven.

## Part A, a separate staging database (Supabase)
1. In Supabase, **create a new project** (e.g. `eje-platform-staging`). Different project = fully isolated
   from production. Note its **Project URL** and **anon public key** (Settings -> API).
2. **Apply the schema:** open the SQL editor and run `supabase-schema.sql` from this repo so staging has the
   same tables.
3. **Seed it with real-ish data:** take the latest snapshot from `backups/<stamp>/` and load each table's
   JSON into staging (a small import script, or Supabase table import). Optionally load only a subset (e.g.
   the `eje` client rows) to keep it light. Never point staging at the production database.

## Part B, a separate staging deploy (Vercel)
Pick ONE:

**Option 1, preview deploys (simplest).** Vercel already builds a unique preview URL for every git branch.
Create a `staging` branch. On that branch, change the two constants in `public/app.html`:
```
var SB_URL = '<staging project URL>';
var SB_KEY = '<staging anon key>';
```
Push the branch. The preview URL now runs against staging. `main` (production) is untouched.

**Option 2, a dedicated staging project.** Create a second Vercel project from the same repo, set its
production branch to `staging`, and put SB_URL / SB_KEY in Vercel **Environment Variables** instead of
hardcoding (cleaner, and it sets up the move away from hardcoded keys that Phase 1 needs anyway).

> Recommendation: start with Option 1 today (5 minutes), move to Option 2 when you tackle Phase 1, since
> Phase 1 removes the hardcoded key from the client entirely.

## Part C, verify
1. Open the staging URL, confirm it loads leads and that the counts match the staging (seeded) data, not prod.
2. Make a throwaway write (mark a test lead) and confirm it lands in the **staging** database, not production.
3. Confirm production (`unabase-app.vercel.app`) is unchanged.

## Guardrails
- Staging keys are still public in the client (same anon-key situation as prod). Fine for staging, and Phase 1
  fixes it everywhere.
- Keep a fresh `backups/` snapshot before promoting any migration from staging to prod.
- Never run a destructive migration against prod that has not first succeeded on staging.

## Done when
You can open the staging URL, it runs against the staging database, a write there does not touch production,
and prod is provably unchanged. From that point on, every Phase 1/2 change is built and proven on staging first.
