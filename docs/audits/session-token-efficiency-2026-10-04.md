# Token efficiency — session retrospective (2026-10-04)
What burned the most context this long session, what we did well, and the rules to cut it next time. Pairs with `docs/WORKING_RULES.md` (the standing rules) and `docs/SESSION_STATE.md` (the one-page handoff that should make a fresh session cheap).

## Biggest consumers (ranked, honest)
1. **Reading large data files into context.** The single avoidable spike: `altavia-run-2-contacts.json` is ~2,863 lines / ~46k tokens, and ~1,300 lines were read before switching to a script. The run-3 JSON and the three-file challenge were handled by script from the start (good), but run-2 was not. **This is the #1 lesson: never read a JSON/CSV data file into context — script it.**
2. **Tool-output logs echoed in chat.** Full per-contact tables from the run-2 / run-3 / 74-record gate passes, the pool-floor JSON, and drain logs. Useful once, expensive when full. Counts + 2-3 samples would have cost a fraction.
3. **app.html round-trips.** Repeated greps + bounded reads to chase the duplicate / click / draft / banner bugs. Mostly necessary (live debugging), but a few reads overlapped.
4. **User-provided screenshots.** 3-4 app screenshots. Image tokens are heavy; these were operator-sent (not controllable), and they were high-value (caught the "(sin borrador)" + fit-score 32 + cut-brief bugs), so this was a good spend.
5. **Fixed overhead.** CLAUDE.md, system reminders, the memory index, tool schemas, deferred-tool fetches. Large but mostly unavoidable per turn.

## What we did WELL (keep doing)
- **Delegated wide reads to subagents.** The provisioning-map agent (~77k subagent tokens) and the two lessons-analysis agents (~44k) did their reading in isolation and returned short reports. That kept tens of thousands of tokens of file content OUT of the main context. This is the highest-leverage habit.
- **Scripted the data instead of reading it.** run-3 (24) and the 74-record gate were processed with scripts that loaded the JSON, verified/deduped, and printed counts + a sample. The file bytes never entered context.
- **Background jobs + Monitor, no polling.** Drains and discovery ran in the background; a single completion line came back instead of a streamed log.
- **Deliverables to MD files, tight chat summaries.** The Codex reviews, the factory-challenge answer, specs, and briefs went to files; chat got the headline + a link.

## Rules to cut it (apply from next session)
1. **Never read a data file (JSON/CSV/log) into context.** Write a 10-line script that loads it, extracts the fields you need, and prints counts + 2-3 sample rows. If you need the schema, print `keys()` of one record, not the file.
2. **Chat gets counts and samples, files get tables.** Any result over ~10 rows goes to a file; the chat message states the counts and links it.
3. **Logs: tail or grep, never cat.** For background work, watch for one terminal line, not the stream.
4. **Grep -> bounded read for code.** Locate with grep, then read only the function/line-range you will edit. Don't re-read a file you just edited.
5. **Delegate any multi-file read to a subagent.** Keep the conclusion, not the bytes. One agent report is far cheaper than reading the files yourself.
6. **Start from SESSION_STATE.md.** Read it first; don't reconstruct state from git history or by re-opening long docs. Update it at session end so the next session starts from one page.
7. **Briefs under 300 words unless asked.** Decision-first, no re-explaining known context.

## One-line verdict
This session was long but mostly disciplined — subagent delegation and script-based data processing saved the most. The one clear miss was reading ~half of a 46k-token JSON before scripting it. Rule #1 (never read a data file; always script it) would have removed the largest avoidable cost.
