# Working rules (token discipline)
Follow these every session, starting 2026-10-04. Goal: a new session starts from one page, not from history, and we stop re-spending context on things we already know.

## Start of session
1. Read `docs/SESSION_STATE.md` FIRST. It is the single source of current state. Do not reconstruct state by reading git history, old reports, or long docs.
2. Read any one reference doc at most once per session. If you need a fact from it again, it should already be captured in SESSION_STATE.md or the relevant code comment. Do not re-open the same doc repeatedly.
3. Do not read `public/*.json` lead files, old audit CSVs, or full briefs unless the task truly needs that exact file. Prefer a count or a `select` over reading a file.

## While working
4. Logs: read the TAIL (`tail -n 40`) or grep for the signal, never cat a whole log into context. For background jobs, watch for one completion line, not the stream.
5. Data: report COUNTS and a 2-3 row SAMPLE, never a full table or full result set. If the operator wants the full set, they will ask or it goes to a file.
6. Code: read the specific function or line range you are changing, not the whole file. Use grep to locate, then a bounded read.
7. Delegate wide reads to a subagent. If answering means reading across many files, spawn an Explore/general-purpose agent and keep only its conclusion. One agent report costs far less context than reading the files yourself.
8. Do not paste large inputs back to the operator. Link the file or give the 3-line summary.

## Writing back
9. Briefs and status updates: under 300 words unless the operator asks for depth. Decision-first, scannable, no re-explaining known context.
10. Update `docs/SESSION_STATE.md` at the end of any session that changed state (pushed code, provisioned a client, moved a decision). It is the handoff. Keep it to one page.

## Hard facts that never need re-deriving (keep here so we stop looking them up)
- Supabase prod ref: `ogdsuztzhmnnjolilsuo`, table `leads` (legacy) + factory tables. PostgREST caps at 1000 rows: paginate (`db.select_all`).
- Deploy: commit changed files by name + `git push origin main`. Vercel serves `app.ejetheagency.com`; Railway auto-deploys the factory from the Dockerfile. Never `git add public/*.json`.
- Factory health: https://factory-production-1e7c.up.railway.app ; nightly self-runs at 06:00 UTC (= 2 AM Miami), set by Railway `FACTORY_RUN_HOUR_UTC=6` (live-confirmed 2026-10-08). `GET /preflight?key=SECRET` checks Serper/Places/MV-credits/Gmail.
- Clients live: `2uplatam` (legacy surface, leave alone), `eje` (EJE's own), `altavia` (demo, one week). Discovery reads `clients.icp_config` only.
- No em dashes, ever. Company email: contact@ejetheagency.com.
