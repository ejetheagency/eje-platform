# Operator seed leads (item 6)

Drop a CSV here named `<client_id>.csv` (e.g. `2uplatam.csv`). The nightly run picks it up and pushes each
row through the normal factory chain: it writes facts (`source_type=operator_seed`, evidence kept), upserts
the company + contact, and creates a DISCOVERED `client_lead`. From there it is treated like any other lead:
Gate A corroboration, Gate B verification if report-bound, gates, READY. **Nothing from the seed skips a gate.**

Each supplied field is tagged with the pivot that would have found it for free (`pivot_name`), so Gate A
learns the recipe to replicate your hand work overnight.

## Columns (header row required; order does not matter, matched by name)

```
company,website,name,role,email,phone,instagram,linkedin,evidence_urls,channel_type,location_evidence,headcount_basis
```

- `company`, `website`: required (at least one).
- `name`, `role`: the named decision-maker and their role.
- `email`, `phone`, `instagram`, `linkedin`: contact channels (as many as you have).
- `evidence_urls`: comma- or semicolon-separated source URLs backing the row (a site page, a profile, a listing).
- `channel_type`: type of the social handles, e.g. `instagram:person;linkedin:person` or `instagram:business`. A business/brand handle is not a personal channel and is not counted as one by the channel gate.
- `location_evidence`: what establishes the operating office(s), e.g. `1 office: 10800 Biscayne Blvd, Miami (contact page)`. A mailing/correspondence address is not an operating office.
- `headcount_basis`: the basis for the employee count, e.g. `LinkedIn 11-50 (self-reported)` or `unknown`. Unknown headcount holds for enrichment, it does not pass.

## Example

```
company,website,name,role,email,phone,instagram,linkedin,evidence_urls
Estudio Fe,estudiofe.cl,Daniela Rojas,Fundadora,daniela@estudiofe.cl,+56912345678,@estudiofe,linkedin.com/in/danielarojas,"estudiofe.cl/nosotros;instagram.com/estudiofe"
```

Re-running is safe: a company already seeded is skipped (idempotent).
