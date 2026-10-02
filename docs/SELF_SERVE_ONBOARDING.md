# Self-Serve Onboarding: Addendum to the Master Plan

> **For the AI assistant reading this in the repo:** This extends `docs/ENRICHMENT_MASTER_PLAN.md`. It defines the end state the codebase is being built toward: a client can sign up, define their ICP, pay, and have the system running for them with no human in the loop. That end state is not built now. What is built now must not block it. The rule in Section 2 is the one that matters today.

---

## 1. The End State

A new client, arriving by word of mouth, with no call and no email from the founder:

1. Opens the app and creates an account.
2. Answers a short guided questionnaire (the **ICP Wizard**) that produces a valid `icps` row.
3. Receives one free report built from the shared global pool (the trial, master plan §6).
4. Pays a subscription in Stripe.
5. The scheduler picks up the new active client that night. The first real report lands at 8 a.m.

No step in that list calls a human. Every step writes to the same tables the system already reads.

---

## 2. The Rule That Applies Today

**Manual onboarding must produce exactly the same data as self-serve onboarding will.**

When the founder onboards a client by hand today, the output of that session is not notes in a doc. It is:

- a `clients` row with plan, timezone, status,
- one or more `icps` rows in the structured schema below,
- a Stripe customer and subscription ID stored on the client.

The ICP session is the founder *being* the wizard. Every question asked in that session that turned out to matter becomes a field in the schema. Every question that didn't is dropped. This is how the wizard gets designed: from the first ten manual onboardings, not from imagination.

Practical consequence for the code now:

- `icps` is a structured table, never a free-text blob. If the founder writes a paragraph, it gets parsed into fields before anything runs.
- There is one function, `onboarding.activate_client(client_id)`, that does everything after payment: validates the ICP, enqueues the first discovery jobs, schedules the daily report. The founder calls it manually today. Stripe's webhook calls it later. Same function.
- No enrichment code reads anything that isn't in `clients`, `icps` or `config`. If a worker needs something the founder "knows" about a client, that is a missing field.

---

## 3. ICP Schema (v1, to be refined by real onboardings)

```yaml
icp:
  id, client_id, name, mode            # mode: broad | account_based
  company:
    industries: [list]                  # from a fixed taxonomy, not free text
    geography: { countries: [], regions: [], cities: [] }
    size: { min_employees, max_employees }   # optional
    age_years: { min, max }             # optional
    required_presence: [website, instagram, linkedin, google_business]
    exclude: [list of industries or keywords]
  contact:
    target_roles: [list]                # e.g. owner, expansion_manager, commercial_director
    entry_roles: [list]                 # account_based only: adjacent roles that count as a way in
    contacts_per_company: int           # 1 for broad, 3-6 for account_based
  signals:
    wanted: [hiring, new_location, active_instagram, website_gaps, recent_reviews]
  volume:
    ready_leads_per_day: int            # bounded by plan
  channels:
    allowed: [email, linkedin, whatsapp, instagram_dm]
  offer:
    one_line_value_prop: string         # used in message personalization
    tone: casual | formal | direct
```

Every field has a default, a validator, and a human-readable question. The wizard is a UI over this schema. The founder's session is a conversation over this schema. The code sees one thing.

---

## 4. Milestones by Client Count

The platform does not need to be self-serve at 10 clients. It needs to be *shaped* for it.

| Clients | Onboarding mode | What the code must have |
|---|---|---|
| **1-10** (now) | Founder does it by hand | Structured `icps`, `activate_client()`, Stripe IDs stored. The founder fills the schema; nothing else is automated. |
| **10-50** | Assisted. An onboarder (hired) runs the session using an internal **ICP form** that writes to the schema directly | Internal admin form over the ICP schema. Validation errors shown before saving. Trial report generated on save. |
| **50+** | Self-serve. The same form, polished, exposed to clients | Public signup, Stripe Checkout + webhooks, the wizard, email verification, the trial-to-paid flow, usage-based upsell prompts. |
| **1,000** | Self-serve is the only mode | Nothing new in onboarding; the work is in scale (master plan §8). |

The internal form at 10-50 **is** the wizard at 50+. It is not rebuilt; the audience changes.

---

## 5. Free Tier (trial): Design Rules

The trial exists to let the product sell itself. It must cost near zero and show real value.

- **What they get:** one report from the shared pool, matching their ICP, with real verified contacts. Enough to send ten messages and get a reply.
- **What they don't get:** daily reports, Tier 2 or Tier 3 enrichment, message generation beyond the first report, templates library.
- **Cost cap:** `plans.trial` in `config/budgets.yaml` allows Tier 1 jobs only, and only against companies already in the pool. Trial accounts never trigger discovery for new companies.
- **Upsell trigger:** the next day's report is locked. The app shows the count of new leads and blurred previews. One button: subscribe. Everything about the lock is config, not code.
- **Abuse guard:** one trial per verified email domain; disposable domains rejected (the email verifier already does this).

Metrics to watch from day one, stored in `metrics_daily`: trial signups, trials that sent at least one message, trial-to-paid conversion, days to convert. These numbers decide what the free tier should contain, not opinion.

---

## 6. What Gets Built, and When

Added to the master plan's phases (§12):

| Phase | Add | Done when |
|---|---|---|
| **1. Foundations** | Structured `icps` schema with validators; `onboarding.activate_client()`; Stripe customer/subscription IDs on `clients` | Founder onboards a client by filling the schema; activation is one function call |
| **5. Experience** | Internal ICP form (admin) writing to the schema; trial report on save; locked-report paywall | A non-founder can onboard a client using only the form |
| **New: 8. Self-serve** | Public signup, Stripe Checkout + webhook -> `activate_client()`, the ICP Wizard (the admin form, client-facing), trial abuse guards, usage-based upsell prompts | A stranger signs up, pays, and gets a report with no human involved |

Phase 8 starts when monthly new clients pass roughly 20. Before that, the admin form plus a hired onboarder is cheaper than the engineering.

---

## 7. Coding Rules Added

1. `icps` is structured. Free text is parsed into fields before use. No worker reads free text.
2. One activation path: `activate_client()`. Manual, assisted and self-serve all call it.
3. Every onboarding question that matters becomes a schema field. Keep a short `docs/decisions/icp-questions.md` recording which questions earned their place and why.
4. Trial limits live in `config/budgets.yaml` under `plans.trial`. The code checks the plan; it never checks "is this a trial" directly.
5. Stripe is the only billing system of record. The app stores IDs and reads status from webhooks; it never computes who has paid on its own.
