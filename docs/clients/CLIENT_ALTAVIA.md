# Client Profile: Altavia Staffing (José Andrés Villena)

> **For the AI assistant reading this in the repo:** Demo client, one week, no payment. Configure, do not special-case. Everything here maps to the ICP schema in `docs/SELF_SERVE_ONBOARDING.md` and to `mode: broad`. The full targeting brief is in `docs/clients/ALTAVIA_BRIEF.md` and is authoritative where this file is short.

## 1. Who the client is

- **Company:** Altavia Staffing (altaviastaffing.com), South Florida phone number. Places experienced bilingual Latin American virtual assistants with US and Canadian small service businesses. Managed model: recruiting, assessment, payroll, supervision, time tracking. No setup fees; clients pay tracked hours.
- **Contact:** José Andrés Villena, decision-maker at Altavia (role title unverified publicly; treat as owner-level per operator). Spanish speaker, Chile timezone. Prefers email or short calls; very protective of his time.
- **Relationship status (2026-10-03):** Cancelled the Monday meeting; signed with a competing agency for lead generation. Accepted a one-week free demo in exchange for feedback. Sunday 10:00 Santiago: 10-minute setup call. The demo is a comparison test against the agency he is paying.
- **What success looks like for the demo:** he logs in Monday, sees 10 to 20 real US or Canadian small-business owners with a reason to talk to Altavia, completes 5 tasks a day, and gets at least one reply inside the week. Feedback Friday.
- **Do not:** export or hand him the contact list as a document. The panel is the product; the list is the asset. Demo clients see leads in the app only.

## 2. ICP (v1, from the operator's brief)

```yaml
icp:
  name: "Altavia · US/CA independent service businesses"
  mode: broad
  client_type: demo              # zero paid spend unless the operator sets a cap below
  company:
    industries: [real_estate_independent, chiropractic, dental, medical_clinic_small, law_firm_small, home_services, gym_fitness_studio]
    geography: { countries: [US, CA] }
    size: { min_employees: 1, max_employees: 50 }
    locations: { max: 2 }
    required_presence: [website]
    exclude: [franchises, chains, groups_dso_msos, three_plus_locations, aca_medicare_insurance_agents, va_job_seekers, property_management_only, marketing_agencies]
  contact:
    target_roles: [owner, founder, broker_owner, owner_dentist, owner_chiropractor, physician_owner, managing_partner]
    entry_roles: [practice_manager, office_manager]
    contacts_per_company: 1
  signals:
    wanted: [vacancy_reception_or_intake, vacancy_dispatcher_or_admin, vacancy_bilingual, spanish_service_page, reviews_missed_calls_or_slow_followup, owner_post_about_workload]
    strong: [vacancy_calls_intake_scheduling_admin_within_30d, owner_statement_needs_help]
  volume:
    ready_leads_per_day: 10
  channels:
    allowed: [email, linkedin, phone]
  offer:
    one_line_value_prop: "Experienced bilingual Latin American virtual assistants, managed end to end, paid by the hour actually worked, no setup fee."
    tone: direct_english
  language: en
```

## 3. Discovery queries (seed, rotate cities)

Rotate US and Canadian metros; do not repeat one market. Templates (substitute CITY):

- `dentist CITY "our team" owner`
- `chiropractor CITY "office manager"`
- `law firm CITY "intake specialist" hiring`
- `real estate team CITY "administrative assistant"`
- `HVAC CITY dispatcher careers` / `plumbing CITY "office manager"`
- `fitness studio CITY owner`
- `dental CITY Spanish receptionist` / `chiropractic CITY "se habla español"`

Google Places discovery works well here: US small businesses list owners on their sites and SMTP verification is far more reliable on US domains than on LatAm ones.

## 4. Gates specific to this client

1. Country US or CA confirmed. Industry confirmed from services, not directory category.
2. Locations 1 or 2. Three or more rejects. Service areas are not locations.
3. 1 to 50 employees. Unknown headcount holds for enrichment, never passes.
4. No franchise, chain, DSO/MSO, or ACA/Medicare agency. Independent agent at a national brokerage: review, not pass.
5. At least one recurring remote task is plausible (calls, intake, scheduling, follow-up, dispatch, admin).
6. A named buyer (owner or manager) with a published business email or direct line. Role inboxes stay parked.

## 5. Message rules

- English. One real fact about the business (the vacancy, the Spanish page, the review pattern). The value prop in one line. A capacity question at the end ("would 20 hours a week of bilingual intake support be useful right now?").
- Never infer ethnicity or language ability from a name. Never claim healthcare or legal compliance.
- Never mention the competing agency.

## 6. Treasury

- `client_type: demo`. Default paid spend is zero. For this week the operator allows: USD 10 total, 50 MillionVerifier credits, within existing provider caps. Log under client_id altavia. No cap raises.

## 7. What to report Friday

Leads delivered, tasks completed by José, replies, which industry and which signal produced replies. That is the feedback we want from the week, and it is also the data for the Strategist.
