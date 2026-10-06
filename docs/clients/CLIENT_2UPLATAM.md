# 2upLatam — client account (contract + billing + system config)

The organized record attached to the `2uplatam` system account. Source of truth for terms + paying dates.
Signed contract PDF + invoices: `~/claude/eje-brand-templates/2uplatam/` (`contrato-2uplatam.pdf`,
`factura-activacion-2uplatam.*`, `factura-suscripcion-mes1-2uplatam.html`).

## Parties
- **Prestador:** EJE — Emiliano Jofre Eyzaguirre · contact@ejetheagency.com
- **Cliente:** 2upLatam — **Fernando José Gonzales** · contactar@2uplatam.com
- **Contrato N°:** EJE-2UP-2026-10 · Emisión 1 oct 2026 · **SIGNED (both parties)**

## Term (vigencia)
- **3 months: 7 oct 2026 → 7 ene 2027.** Initial 3-month commitment.
- System active + implemented as of **7 oct 2026**.
- **Evaluation / continuity meeting: ~15 days before term end → ~23 dic 2026** (tentative, confirm with Fernando). Decides renewal + eventual ICP/geo/template expansion.

## 💲 Billing — paying dates (the thing to never miss)
| Concept | Amount | When | Status |
|---|---|---|---|
| **Activación** (one-time, non-refundable) | **USD 100** | week after ICP mtg, before 7 oct | (confirm paid) |
| **Base mensual** | **USD 200/mo** | **7 oct · 7 nov · 7 dic 2026** (day 7) | 7 oct due now |
| **Variable · por cliente cerrado** | **USD 70 / close** | billed separately after each period's results | as closes happen |

- Variable charges **only when 2uplatam closes a client** from a system-generated conversation. No per-meeting charge, no other variable.
- Payment: **Stripe, USD**, via the charge link EJE sends per concept. Confirmation to contact@ejetheagency.com.
- **Late base payment → EJE may suspend system access** until regularized (does not extend term or waive accrued fees).
- Reminder cadence to set: base charge on the **7th** each month; variable reconciled at period close.

## What EJE delivers (objeto)
The **Generador de Conversaciones Accionables**: identifies, enriches, and delivers **qualified decision-makers daily**, each with a ready first message + the right contact channels, configured to 2uplatam's ICP. **The system does NOT auto-send** — 2uplatam's team executes each contact via the guided one-click steps. Best-effort; no guaranteed # of meetings/closes.

## ICP (contractual config)
- **Emprendedor con techo:** owner-verifiable business, **1-3 years old**, tangible/physical presence.
- **Focus: decisoras mujeres** (female decision-makers), broad business areas, refined by conversion results.
- **Market: Ecuador** — Sierra Norte, capital (Quito), Sierra Sur, Costa.
- **Volume target: 20 decisores/día — CONTRACTUAL reference volume.** (This is why factory yield for 2uplatam is an obligation, not a nice-to-have. Set `icp_config.ready_leads_per_day = 20`.)
- 2uplatam's own offer (what THEY sell to these decisores): a **Scale Hub** — entry product = a **consultoría (USD 500)**, then a qualified few go to ongoing acompañamiento + acceso a capital + red de contactos. (Composer grounded on this; the "export" angle was a composer error, corrected.)
- Expansion to Colombia / Perú = only by written agreement.

## Other terms
- **Support:** 2-4 hrs/week availability for questions + accompaniment, whole term.
- **IP:** EJE owns the system/method/templates/engine; 2uplatam gets a non-exclusive license during the subscription; delivered contact data is theirs to use.
- **Data:** EJE sources from public/legitimate sources; 2uplatam responsible for lawful use in its jurisdiction.
- **Liability:** capped at fees actually paid in the period of the claim. Independent contractors. Confidentiality both ways.
- **Termination:** 3-month commitment; early term only for grave breach (written); on termination access ceases, accrued fees stay due, activation non-refundable.
