# Treasury: Addendum to the Master Plan

> **For the AI assistant reading this in the repo:** This expands §5 D8 of `docs/ENRICHMENT_MASTER_PLAN.md` from a budget guard into a full financial department. Build it as a first-class service with its own tables, its own worker, and a live admin view. It is not optional and it is not "later": nothing in Tier 1, the Pivot Engine or Tier 2 may make an external call without going through it. Margins are protected here or nowhere.

---

## 1. What the Treasury Is

Three jobs, in order of importance:

1. **Protect.** No call is made that would break a cap: per client, per provider, per day, or globally. A kill switch stops all paid spend in one flag.
2. **Distribute.** For every call that could be served by more than one provider, choose the provider with the most headroom *right now* (free quota left, credits left, rate limit not hit), not the one that is hardcoded first. Budget flows to where it exists.
3. **Forecast and improve.** Know the spend of the next 10 days by provider, know the margin of every client, and surface the changes that would raise margin: a cheaper provider for the same result, a pivot that costs more than it earns, a client priced below their cost.

The founder's test of success: open the admin page at any hour and see, live, what is being spent, on what, for whom, and how much room is left. Nothing hidden, nothing estimated after the fact.

---

## 2. Data Model

```
provider_accounts
  provider, plan_name,
  billing_model,            # credits | tokens | requests | flat_monthly
  period_start, period_end, # the provider's own billing window
  quota_free,               # free units this period (e.g. 2,500 Serper queries)
  quota_paid,               # purchased units this period
  used_free, used_paid,     # live counters, updated on every call
  unit_cost_usd,            # cost of one paid unit (0 for free tier)
  rate_limit_rpm, rate_limit_rpd,
  last_429_at, cooldown_until,
  updated_at

cost_ledger                 # one row per external call, written by the adapter, never by the caller
  id, ts, provider, client_id, lead_id, job_type, pivot_name,
  units, unit_cost_usd, cost_usd,
  was_free_tier,            # true if served from free quota
  result_status             # ok | empty | error | rate_limited

budgets                     # read from config/budgets.yaml at boot, mirrored here for live edits
  scope,                    # global | plan | client | provider
  scope_id,
  window,                   # day | month
  cap_usd, cap_units,
  soft_pct                  # alert threshold, e.g. 0.8

revenue
  client_id, period_start, period_end, mrr_usd, source (stripe)

metrics_finance_daily       # computed nightly, read by the admin page
  date, provider, client_id,
  spend_usd, calls, free_calls, paid_calls,
  forecast_10d_usd, headroom_units,
  margin_pct                # per client: (mrr - spend) / mrr
```

The only writer to `cost_ledger` is the provider adapter layer. If a call happened, there is a row. If there is no row, the call did not happen. This is enforced by code review and by a nightly check that compares the ledger against each provider's own usage dashboard where an API for it exists.

---

## 3. The Allocator (the distributor)

Every request from a worker is a *capability request*, not a provider request:

```
treasury.acquire(capability, client_id, est_units=1) -> Grant | Denied
  capability: llm_cheap | llm_premium | web_search | page_fetch | email_find | email_verify | logo | places
```

`acquire()` does, in this order:

1. **Kill switch.** If `kill_switch_paid_spend` is on and the capability has no free provider with headroom, deny.
2. **Client cap.** Check the client's plan cap for this capability's cost class for today and this month. Deny if exceeded. Trial clients can only receive grants that cost 0.
3. **Candidate providers.** From `config/providers.yaml`, list providers that serve this capability, ordered by: free quota remaining (desc), then paid credits remaining (desc), then unit cost (asc), then quality score for this capability (desc).
4. **Exclusions.** Skip any provider in cooldown (recent 429), over its rpm/rpd, or whose own period cap is reached.
5. **Grant.** Reserve `est_units` on the chosen provider (increment a pending counter so parallel workers don't all pick the same last free unit), return a `Grant{provider, reservation_id}`.
6. **Settle.** The adapter calls `treasury.settle(reservation_id, actual_units, status)` after the call. This writes the ledger row and releases the reservation. An unsettled reservation expires after 60 seconds and is released.

The caller never names a provider. That is the whole point: when Gemini's free tier runs out at 2 a.m., calls flow to Groq, then Cerebras, then paid Flash-Lite, with no code change and no human awake.

Priorities for a tie: free before paid, always. Among paid, cheapest unit that meets the capability's minimum quality score. Quality scores come from the Strategist (Pivot Engine §5): a provider that finds emails that get replies outranks one that finds emails that bounce.

---

## 4. Forecast (the 10-day rule)

A nightly job, `treasury.forecast`, computes per provider and per client:

```
burn_rate_7d       = spend over the last 7 days / 7
forecast_10d       = burn_rate_7d x 10 x growth_factor
growth_factor      = (active_clients_today / active_clients_7_days_ago), floored at 1.0
headroom_days      = remaining_units / (units_per_day_7d_avg)
```

Outputs:

- **Reorder alert** if `headroom_days < 10` for any provider: "Buy N units of X by date D (cost $C)." Sent to the founder by email and shown on the admin page. The N is sized so the next purchase covers 30 days at the forecast rate.
- **Margin alert** if any client's `margin_pct < max_cost_ratio` (master plan §7, default 80% margin, i.e. cost <= 20% of MRR) for two consecutive weeks. The alert includes the top three cost drivers for that client (by provider and by pivot).
- **Plan alert** if the average cost per client in a plan exceeds the plan's target. This is the signal to reprice or to tighten the plan's volume config.

Forecast accuracy is itself tracked: last week's forecast vs. this week's actual, stored in `metrics_finance_daily`. If error exceeds 20% for two weeks, the growth factor logic is the first suspect.

---

## 5. Improve (the part that raises margin)

Weekly, `treasury.optimize` produces a short report, written to `docs/finance/weekly-<date>.md` and shown on the admin page. It contains only findings with a dollar figure attached:

| Finding type | How it is computed | Example output |
|---|---|---|
| Cheaper provider available | Same capability, two providers, quality score within 5 points, cost differs | "Switch email_verify from Hunter to self-hosted verifier for domains on Google Workspace: -$42/month at current volume" |
| Pivot that loses money | Pivot cost per verified contact > plan's cost ceiling per contact, by ICP type | "Pivot `linkedin_search` costs $1.80 per verified contact for banks ICP; ceiling is $0.60. Lower its allocation." |
| Free tier underused | Free quota remaining at period end > 20% | "Cerebras: 380K tokens/day unused. Raise its priority for llm_cheap." |
| Client below margin | Section 4 | "Client X: 68% margin, driver is Apollo lookups. Options: raise price, cap Tier 2, or shift to Icypeas." |
| Duplicate spend | Same (provider, company, capability) paid twice within TTL | "17 duplicate Serper queries this week; cache miss in page_fetch. -$0.02 each, but it's a bug." |

Nothing in this report is applied automatically. The founder approves; config changes. The report's job is to make sure the decision is never missed and always has a number on it.

---

## 6. The Live View (what the founder's brain wants to see)

An admin page, `/admin/treasury`, driven by a websocket or server-sent events from the ledger. It is a real animation of the department working, not a chart that refreshes every minute.

**Top band, always visible:**
- Spend today (live counter), spend this month, forecast 10 days, MRR, blended margin.
- Kill switch state, with the button.

**Provider rail, one card per provider:**
- A bar: free used / free total, paid used / paid total. The bar moves as calls settle.
- Rate: calls per minute right now.
- Headroom days. Turns amber under 15, red under 10.
- Cooldown badge if in 429 backoff.

**Flow panel, the animation:**
- Each settled call appears as a dot that travels from the worker that requested it (Scout, Pivot, Gates, Contact, Writer) to the provider that served it, colored by cost class (free = teal, cheap = indigo, paid = amber). Dots for denied requests bounce off the Treasury and show the reason on hover.
- This is cosmetic in engineering terms and it is still required. It is how a human verifies, at a glance, that the distributor is doing what it should: dots should overwhelmingly land on free providers, and paid dots should only appear after free rails fill.

**Client table:**
- Per client: plan, MRR, spend this month, margin, top cost driver, status (ok / amber / red).

**Alerts strip:** reorder, margin, plan, forecast-error alerts, newest first, each with the one-line action.

Everything on this page reads from `cost_ledger`, `provider_accounts` and `metrics_finance_daily`. It never calls a provider itself.

---

## 7. Where It Runs

- `treasury.acquire/settle`: a library imported by every worker, backed by Postgres (Supabase). Reservations use a single `UPDATE ... RETURNING` so concurrent workers never double-grant.
- `treasury.forecast`, `treasury.optimize`, the nightly ledger reconciliation: scheduled jobs (pg_cron -> Edge Function, or the Railway worker container).
- The live view: a small Node/Next route on Vercel subscribing to Supabase Realtime on `cost_ledger` inserts. The web app stays read-only.
- Provider usage sync: where a provider exposes a usage endpoint (Apollo, Hunter, Serper, Stripe), pull it hourly into `provider_accounts` so the counters are checked against the source of truth, not only against our own ledger.

---

## 8. Rules (non-negotiable)

1. **No provider call without a Grant.** Adapters refuse to run without a `reservation_id`. A linter rule or a test asserts that no file outside `/packages/providers` imports a provider SDK.
2. **The ledger is append-only.** Rows are never edited or deleted. Corrections are new rows with a negative amount and a reason.
3. **Free before paid, always.** The allocator's first sort key is free headroom. Changing this requires a decision note in `docs/decisions`.
4. **Trial costs zero.** A trial client's grants must have `unit_cost_usd = 0`. Any paid grant to a trial client is a bug, and the nightly check fails the build.
5. **Every cap lives in `config/budgets.yaml`.** The code reads caps; it never contains them.
6. **Margin is per client, computed from Stripe revenue, not from list price.** Discounts, failed payments and churn show up in the margin the same week they happen.
7. **Forecast every night, reconcile every night, optimize every week.** If any of the three jobs did not run, the admin page shows it in red at the top.
8. **The kill switch is one flag, honored by `acquire()`, with no bypass path.** It stops paid spend within one reservation timeout (60 s) across every worker.

---

## 9. Build Order (slots into master plan §12)

| Phase | Build | Done when |
|---|---|---|
| 1 | `cost_ledger`, `provider_accounts`, `budgets` tables; `acquire()`/`settle()` with reservations; kill switch; adapters refuse calls without a Grant | A test runs 50 parallel workers against a provider with 10 free units; exactly 10 free grants are issued, the rest fall to the next provider or are denied; the ledger has one row per call |
| 2 | Allocator sort order (free -> paid -> cost -> quality); cooldown on 429; client plan caps | Exhausting Gemini's free tier in a test moves traffic to Groq without code changes |
| 3 | Nightly forecast; reorder and margin alerts by email; Stripe revenue sync; provider usage sync | A forecast email arrives with a reorder instruction before any provider runs dry |
| 4 | Weekly optimize report with the five finding types | The report names at least one dollar-quantified change in its first week |
| 7 | Live admin view with provider rail, flow animation, client table, alerts | The founder watches a night shift and can tell, without reading logs, that paid calls only follow free ones |
