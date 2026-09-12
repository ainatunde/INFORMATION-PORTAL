# Portal Build Plan v2

**Date:** 12 September 2026
**Status:** proposed — supersedes the Phase 1 implementation plan
**Settled:** 12 Sep — every portal MCS-owned (Q4) · no stored case descriptions (Q3) · graduated auto-publish (Q2)
**Baseline:** Master Review + Phase 1 implementation plan. Master Plan v1 is historical reference only.
**Published version:** https://claude.ai/code/artifact/dc28d1e7-7f7f-4474-948c-efdac1b668db
**Companion:** `2026-09-12-third-reading.md`

Same destination as the attached implementation plan, reordered around one structural change:
**the first shippable product contains no AI at all.**

| | |
|---|---|
| **Scope** | One shared archive, two portals. Immigration is domain pack #1 |
| **Shape** | 3 data layers, 6 build stages each with an exit test, 2 parallel tracks |
| **Effort** | 24–31 engineering days to full Lane A + Lane B (one full-time engineer) |
| **First live output** | End of Stage 3 — ~12 days in, zero AI spend |

---

## §1 What carries over intact

v2 is a reordering and a tightening, not a replacement. Kept verbatim from the attached plan:

- The **module layout** — `core / models / schemas / ingestion / pipeline / api`.
- **Config-driven tenants and sources** in YAML, with all tenant *tooling* deferred. Deferring the
  tooling is the best call in the document — no gold-plating. Where the tenancy *data model* goes is
  a separate question; v2 got it wrong on the first pass and §3 corrects it.
- **Dual Postgres / SQLite** via async SQLAlchemy, so the suite runs with no Docker.
- The **two anchor routes** — UK Skilled Worker and Canada Express Entry category-based selection.
- The **stack** (FastAPI, Pydantic v2, SQLAlchemy 2, httpx, feedparser) and the **endpoint shapes**.
- The **zero-scrape principle**: GOV.UK Content API and IRCC RSS, no HTML scraping, no appointments.

## §2 The two lanes, and why Lane A ships first

The attached plan has one publishing path, and everything waits on the AI step — which is the
hardest, slowest and most expensive part to make trustworthy.

**Lane A — Notice.** Deterministic, automatic, seconds. Authority's headline, official URL,
`retrieved_at`, content hash. No interpretation, so essentially none of the regulated-advice risk.
It is a product on its own: *"the rule changed, here is the official document, we saw it at 09:14."*

**Lane B — Interpretation.** What changed, prior value, who it affects. Where the model runs, where
the liability lives, and the only thing needing a human before publication. Attaches to the notice
as an update rather than replacing it.

```
GOV.UK API / IRCC RSS
        ↓
Snapshot  (bytes → object store, hash → Postgres)
        ↓
Hash changed? ──no──→ log and discard
        ↓ yes
LANE A · Notice  (headline · official URL · retrieved_at · hash)
        ├──────────────────→ Telegram / WhatsApp / feed        [seconds, no AI]
        ↓
Extraction (tiered model router)
        ↓
Diff vs previous fact (reasoning tier)
        ↓
Risk tier (deterministic table)
        ↓
Quarantine → human review → approve
        ↓
LANE B · Interpretation (attached to the notice) → follow-up alert
```

**Consequence for build order:** Lane A needs no model, prompt, API key, token budget or review
queue — just an HTTP client, a hash function and a Telegram token. So a live, useful, legally
defensible product exists at the end of Stage 3 (~11 engineering days), and the AI effort is then
spent on a running system with real traffic and real user questions instead of on an unvalidated
guess about what to extract.

It also resolves the third reading's contradiction: you can sell an *instant* alert and still gate
everything risky, because the instant thing and the risky thing are no longer the same object.

### §2.1 Lane B is the product, not the human gate

The naming invites a conflation worth clearing up. **Lane B is the interpretation product** — the
threshold moved from X to Y, effective D, here is who it affects. The human review is a *policy
applied to* Lane B, not Lane B itself. Lane B can be fully automated. The question is never whether
to have it, only whether a person sits in it and for how long.

It is not optional on either axis. **Commercially**, Lane A alone is a link-dropper: anyone can build
RSS-to-Telegram in an afternoon and nobody pays for it. Every item in the revenue model — the
dossier, the premium alert, the B2B policy dashboard, the historical API — is *what changed and what
it means for me*. Lane A builds the audience; Lane B is what you sell. **Technically**, Lane B *is*
the archive: extraction is what produces structured temporal facts, so without it there are no
`policy_fact` rows, no supersession chain, and no answer to "what did this rule say in March 2024".
Lane A stores documents. Lane B turns them into data, and the moat is in the data.

### §2.2 Earning full automation instead of assuming it

v1 §1 already set the operating model as *"automated by default, exception-routed, minimal daily human
involvement"*, and v1 §8's publication rules already route low-confidence items to quarantine and
unsupported legal conclusions to blocked. A human exception path was always in the plan. What follows
is not an addition to it — it specifies *which* exceptions route, and how that set shrinks with
evidence.

The reason not to auto-publish everything on day one is simply that **the error rate is unknown until
the Stage 4 corpus exists.** And the error is asymmetric in a way that cannot be refunded: a wrong
salary threshold means someone submits an application, pays several thousand pounds in non-refundable
fees and health surcharge, is refused, and carries a refusal history. A wrong reading on
exit-and-reapply can trigger a multi-year re-entry bar. Against a positioning built entirely on being
the accurate source, one viral error costs more than the review ever did.

| Risk class | Examples | At launch | Promotion rule |
|---|---|---|---|
| **1 — Restatement** | Fee amount, form version, processing time, office change | **Automatic** | None needed — template-rendered restatement with a citation, no comparative claim |
| **2 — Comparative** | Threshold X→Y, occupation added to or removed from a list, CRS cutoff | Human | Automatic after 50 consecutive approvals with zero material corrections in that class |
| **3 — Consequential** | Grandfathering, transitional provisions, who is affected | Human | Only by explicit decision with legal input |
| **4 — Never** | Overstay, unlawful presence, anything where acting on it could trigger a bar | Human always | Arguably not Lane B at all — route to the legal partner |

Every review is a free labelled data point, so the calibration set accumulates while you operate.
Class 1 is automatic from day one; Class 2 is the bulk of the volume and should clear its gate within
weeks. The realistic destination is **80–90% of Lane B auto-publishing within a few months**, with a
person on only the handful of items that can genuinely ruin someone — which is what "automated by
default, exception-routed" means in practice. Two things keep the cost down: the load at Tier 1 is
one to seven hours a week, and per D21 a fact is reviewed once and published to N portals, so review
effort scales with countries, never with portals.

## §3 The factory: what multi-tenant actually requires

v2's first pass treated multi-tenancy as a feature to defer rather than a force shaping the schema,
and one Stage 1 line was wrong: *"tenant FK on every content row."* Put a tenant key on content and
you get one of two bad outcomes — the same GOV.UK snapshot stored once per portal, destroying hash
deduplication and splitting the archive that is supposed to be the moat, or a later migration that
rewrites every query and every route. It also makes v1 acceptance criterion #15 — *"one source can
produce different tenant-specific outputs"* — unsatisfiable by construction.

### §3.1 Three layers, and only one knows about tenants

1. **Archive — tenant-agnostic.** `Source`, `ContentSnapshot`, `PolicyFact`. One globally
   deduplicated copy of what the authorities published. No `tenant_id`, ever.
2. **Subscription — configuration.** Which sources, routes, categories and risk thresholds a portal
   cares about. Lives in `tenants.yaml`.
3. **Publication — tenant-scoped.** A fact rendered *for* one portal: its template, disclaimer,
   channels, state, publish timestamp. The only content table carrying `tenant_id`.

One ingestion, N publications. That is the unit economics of the factory, and the reason the archive
argument gets *stronger* with each portal: VisaTrack and SkilledPath both consume the same UK
threshold change at no extra fetch, storage or extraction cost. A second portal is close to pure
margin on the ingestion side.

It also fixes the review arithmetic. Review the **fact** once, then let publication rules fan it
out. Review per published item and the human queue multiplies by portal count — the third reading's
staffing estimate survives two portals and breaks at three.

### §3.2 Two axes: the domain pack is code, the tenant is config

The gap none of the three documents close. v1 promises *"adding a new portal must not require a new
codebase"* and lists *"AI instructions"* and *"content templates"* as per-tenant configuration, with
`theme: immigration` as a bare string. But extraction schemas and prompts cannot safely be free-text
config — that is precisely the hallucination surface the Master Review spent its length closing.

```
domain_pack  # CODE. versioned, reviewed, corpus-tested.
  extraction_schemas   Pydantic models per route
  prompts              per schema, versioned with the pack
  risk_table           topic × magnitude × reliability
  render_templates     fixed prose templates
  taxonomies           { SOC 2020, NOC 2021 TEER, … }
  adapters             which ingestion adapters it binds

tenant       # CONFIG. a YAML file. no code.
  domain_pack          "immigration"
  routes               subscription into the pack's routes
  domain, branding     host, logo, theme tokens
  channels             telegram, whatsapp, email
  disclaimers, plans   text and commercial config
```

The commercial consequence is the takeaway:

- **VisaTrack → SkilledPath is cheap.** Same domain pack, different route subscription, branding and
  taxonomy emphasis. Days, mostly content. v1's claim is true for this case.
- **VisaTrack → GrantTrack or TenderTrack is a new domain pack.** New schemas, prompts, risk table,
  and its own golden corpus before it can be trusted. Weeks, and it is engineering, not config.

v1's Phase 7 "portal creation wizard" implies these are the same exercise. They are not, and costing
them the same way is how a portal-factory thesis fails in year two — you promise a new vertical in a
week, then discover the extraction layer must be rebuilt and reviewed from scratch. Plan the wizard
for axis two only: it spins up *tenants*, never *domain packs*.

### §3.3 Multi-brand, not SaaS — settled, and it deletes a category of work

**Confirmed 12 September: every portal is owned and operated by MCS.** That makes this multi-brand
single-operator, not software-as-a-service. No tenant is an adversary, none has a contract with you,
and none can be given a security guarantee it might later enforce. This is the cheapest available
answer, and it permanently removes work rather than deferring it.

| Deleted, not deferred | Stands regardless |
|---|---|
| Row-level security and schema-per-tenant isolation. Application-level scoping on the publication layer is sufficient | The three layers — they exist for deduplication, the archive and review-once, not for isolation |
| Per-tenant secrets, credentials and key rotation. One platform secret set | Host-based tenant resolution — portals still need to look independent on their own domains |
| Noisy-neighbour quotas and per-tenant fairness limits | Public API rate limiting, for abuse prevention rather than fairness |
| Self-serve onboarding and a tenant provisioning product. A new portal is a YAML file, a PR and a DNS record — a runbook, not a feature | Tenant on every audit row — you still need to know which portal an action touched |
| Per-tenant SLAs, support tooling and a tenant-facing console. MCS staff work one internal ops view across all portals | Revenue and analytics reported per portal — v1 criterion #19, which is reporting, not tenancy infrastructure |
| Data residency per tenant, and the archive licensing question — MCS owns the archive outright and resells it as it chooses | One staff RBAC model with roles, rather than per-tenant user pools |

**The inference to avoid.** "MCS owns every tenant" does **not** mean the three-layer split can be
skipped. None of D17–D21 exist for isolation. They exist because one snapshot must serve N portals
without duplication, because the archive compounds only if shared, and because a fact reviewed once
must publish to many — all true whoever owns the tenants. Collapsing the layers because nobody
outside would complain is how you get the per-portal archive duplication §3 was written to prevent.

One genuine risk arrives with this answer, and it is cultural rather than technical. Because no
external party would object, keeping portals distinct becomes self-imposed discipline: it will be
tempting to surface SkilledPath content inside VisaTrack, or to mail every user about every portal.
Both undermine the "independent, focused portal" positioning that is the point of the factory — and
per §3.4 both may breach the consent under which the data was collected. Keep publication boundaries
enforced in code even though nothing outside the company requires it.

### §3.4 The question MCS ownership raises instead: one audience or several?

Settling ownership surfaces a different question. A Nigerian tradesperson is plausibly both a
VisaTrack and a SkilledPath reader; the commercial thesis is explicitly cross-portal. So does a user
who signs up on one portal have an account on the other?

**Recorded default: shared identity, portal-scoped subscriptions and consent.** The same shape as the
content model — `user` is tenant-agnostic, and a join table carries which portals they subscribed to,
on which channels, under which consent. Separate identity per portal doubles the authentication
surface for no benefit when you own both sides, and forecloses the cross-sell that makes the second
portal worth building. Presentation stays independent regardless: the reader never sees "MCS
Information Cloud".

One constraint travels with it — the NDPA point from the third reading, in a new place: **consent is
per portal and per purpose.** A user who consented to UK policy alerts on VisaTrack has not consented
to SkilledPath trade marketing, and a shared identity table makes that boundary easy to cross by
accident. Store the consent record against the join, not against the user, so the lawful basis is
checked at the point of sending. No user accounts exist before Stage 6 in any case, so nothing here
is built yet — but deciding it now costs nothing and deciding it later costs a migration.

### §3.5 What this changes, and what it does not

It adds roughly a day to Stage 1 and changes nothing downstream, because the stages already put the
schema first. It does **not** pull the admin console, theme manager, portal wizard, per-tenant
billing or a second domain pack into scope — those stay deferred exactly as the attached plan had
them, and that judgement was right. The change is confined to the shape of the tables plus one extra
exit test: *one ingested fact, two portals, two renderings, one archive row.* If Stage 1 passes
that, the factory is real rather than aspirational.

---

## §4 Two tracks that start before Stage 1

### §4.1 Track A — Clearances (file all six on day one)

| Item | Gates | Owner |
|---|---|---|
| Managed transactional email, production access | Any email. Accounts start sandboxed/capped; production access can be refused; warm-up follows approval | CTO |
| Domain, DNS, SPF/DKIM/DMARC | Email plus brand. Sending reputation cannot be bought late | CTO |
| Meta business verification → WhatsApp Cloud API | The paid alert tier. Needs verified entity and documents | Tunde |
| Paystack / Flutterwave merchant onboarding | All revenue. Needs CAC registration and compliance review | Tunde |
| 3–5 licensed legal partners under contract | Primary revenue engine. Longest lead time — enterprise sales with legal negotiation | Tunde |
| Data-protection position (NDPA 2023) | Lead gen and user accounts. Determines what may be collected → determines the schema, so it gates **Stage 1** | Tunde + counsel |

### §4.2 Track B — Manual validation (no code)

- **Run Lane A by hand, now.** Telegram channel, UK/Canada updates posted manually in the notice
  format, two weeks. Tests whether an audience forms, reveals from the replies which fields people
  actually ask about, and seeds the distribution list Stage 3 then takes over.
- **Sell five dossiers by hand.** Bank transfer, hand-written PDF. Five sales is a real
  willingness-to-pay signal; zero is the most valuable finding available, at a cost of two days.

Writing five dossiers manually tells you which extraction fields matter far better than designing
the Pydantic schema in the abstract — Track B is a genuine input to Stage 4.

## §5 The build, stage by stage

Sequenced by dependency, sized in engineering days for one competent full-time engineer.

### Stage 1 — Spine and the three layers · 4–5 days
- This repository. Alembic migration from the first table.
- **Three-layer separation** (§3): archive tables carry no `tenant_id`; a `Publication` table is the
  only tenant-scoped content layer.
- Temporal fact schema (§5.1): `valid_from`, `valid_to`, `superseded_by`, citation triple, taxonomy
  edition, plus `domain_pack` + `pack_version` stamps.
- `ObjectStore` interface — local FS now, R2 later. Postgres never holds raw bytes.
- `AuditLog` on every state transition, append-only, carrying actor *and* tenant.
- `tenants.yaml` / `sources.yaml` validated at startup; tenant resolved by host so routing is never
  hardcoded.

**Exit test:** migration clean on Postgres *and* SQLite; a snapshot lands as bytes on disk with only
hash/pointer/metadata in the DB and one audit row; persisting a fact without a resolvable citation
triple raises. **And the factory test: one ingested fact publishes to two tenants with different
templates and disclaimers, from a single archive row, with no duplicated snapshot.**

### Stage 2 — Ingestion and change detection, zero AI · 4–5 days
- GOV.UK Content API adapter; IRCC RSS/Atom adapter.
- Source registry behaviours v1 required and the attached plan omits: rate limit, timeout, retry
  with backoff, failure count, auto-disable, last-success tracking.
- SHA-256 snapshot hashing and diff against latest per source; duplicates logged and discarded.
- Ingestion still synchronous behind `POST /api/v1/ingest/run` — deliberately, and recorded as such.

**Exit test:** run twice against a live source — one snapshot, one discard, no duplicate rows;
mutate a fixture — exactly one change event; point a source at a failing endpoint — it retries,
counts failures and disables itself without affecting the other source.

### Stage 3 — Lane A, Notice publishing · 3–4 days · **SHIPS**
- Notice built deterministically from the snapshot: headline, official URL, `retrieved_at`, hash,
  source, route tags.
- Prose rendered from a **fixed template over structured fields**, not generated.
- Telegram dispatcher, idempotent per notice.
- `GET /api/v1/portal/{tenant}/feed` with citations and disclaimers.

**Exit test:** a real GOV.UK or IRCC change produces a Telegram message in under 60 seconds with a
working official link, retrieval timestamp and hash — and the same change re-ingested posts nothing.
Token spend to date: zero.

### Stage 4 — Extraction, first AI · 5–7 days
- **Model router**, two tiers (fast extraction / reasoning diff), selected by config. No model name
  in code. Per-call cost and latency recorded.
- Pydantic extraction schemas for the two anchor routes, emitting temporal facts.
- **Golden fixture corpus**: ~20 real historical policy documents with hand-verified expected
  extractions. Recorded-response mode so the suite never bills an API.
- Redis and a worker queue introduced here, where model latency justifies them.

**Exit test:** ≥90% field-level accuracy across the corpus with failures enumerated; full suite runs
offline with no spend; cost per change recorded and under $0.03; swapping the configured model
changes no application code and reruns the corpus.

### Stage 5 — Lane B, diff, risk and review · 5–6 days
- Diff analyser comparing fact N to N−1 on the reasoning tier; supersession written back
  (`valid_to`, `superseded_by`) atomically.
- **Deterministic risk tiering**: versioned, unit-tested table of topic × magnitude × source
  reliability. Thresholds, quota cutoffs, overstay and unlawful presence always route to review.
- Review queue: list, approve, **reject with reason** — both writing immutable audit rows with
  reviewer identity.
- **Graduated auto-publish** (§2.2): risk classes 1–4, Class 1 automatic from launch, and a per-class
  counter of consecutive clean approvals that promotes Class 2 to automatic once its threshold is
  met. The counter resets on any material correction.
- Approved interpretation attaches to its notice and dispatches a follow-up.

**Exit test:** a historical UK threshold change replays end to end — notice fires immediately,
interpretation quarantines, a named reviewer approves, follow-up dispatches, prior fact marked
superseded with a pointer, every step reconstructable from the audit log alone. Reject path verified.
A Class 1 item publishes with no human touch, and a Class 4 item cannot be auto-published even when
its counter would otherwise allow it.

### Stage 6 — Durability · 3–4 days
- R2 implementation of `ObjectStore` swapped in behind the Stage 1 interface.
- Automated Postgres backup to an **off-provider** destination. Stated RPO and RTO.
- Snapshot immutability: append-only, hash-chained, never updated in place.
- Secrets out of the repository, API rate limiting, ingestion idempotency keys.

**Exit test:** restore DB and object store into a clean container from backups alone and verify the
hash chain end to end. Write the drill up. An untested backup is a belief, not a backup.

### Out of scope for v2
VisaTrack Verify, payments, the B2B lead flow, SkilledPath, any tenant-management UI. Each is gated
on Track B results and Track A clearances, and deserves its own plan. Verify should not start until
the defamation and right-of-reply constraints are written down as product requirements — highest
legal exposure, lowest direct revenue.

### §5.1 The record every stage is built around

```
policy_fact   # shared archive — no tenant_id, ever
  domain_pack      "immigration"
  pack_version     "1.3.0"         # which schema produced this fact
  route            "uk.skilled_worker"
  field            "general_salary_threshold"
  value            { amount, currency }
  valid_from       date
  valid_to         date | null     # null = current; set on supersession
  superseded_by    fact_id | null
  taxonomy         { scheme: "SOC", edition: "2020" }
  citation
    url            official source URL
    retrieved_at   timestamp
    content_sha256 hash of the archived bytes
  risk_tier        enum — deterministic table, stage 5
  lane             notice | interpretation
  confidence       float | null

publication    # the only tenant-scoped content layer
  tenant_id        fk
  fact_id          fk → policy_fact
  template         tenant's render template
  disclaimer       tenant's disclaimer text
  channels         [telegram, whatsapp, feed]
  state            draft | published | withdrawn
  published_at     timestamp | null
```

Three fields separate an archive from a news feed. The **validity interval and supersession pointer**
answer *"what did this rule say on 14 March 2024"* — the only question a competitor polling the same
public API cannot answer. The **citation triple** ties every claim to the exact bytes seen. The
**taxonomy edition** prevents silent corruption in year two: UK SOC and Canadian NOC both get
revised, codes get reused with changed meanings, and an unstamped mapping starts returning wrong
occupations with no error anywhere.

## §6 Divergence from the attached implementation plan

D1–D4 and D17–D18 are structural and the rest follow from them; the remainder are independent and
can be taken piecemeal.

| # | Attached plan | Plan v2 | Why |
|---|---|---|---|
| **D1** | Single publish path; everything waits on AI extraction | Two lanes; Lane A ships at Stage 3 with no AI | Earlier live product, safest legal posture first, resolves the instant-alert vs human-gate contradiction |
| **D2** | Target `C:\Users\aina_\.gemini\antigravity\scratch\mcs-platform` | This repository, on the working branch | A platform whose value is an immutable audit trail cannot begin outside version control |
| **D3** | `ContentSnapshot` stores raw text/payload in the DB | Bytes to an `ObjectStore` (local FS, then R2); DB holds hash, pointer, metadata | Contradicts the Master Review's own §2.4. Postgres becomes an HTML landfill and backups become unusable — which is the moat |
| **D4** | Extraction schema carries `effective_date` | `valid_from` / `valid_to` / `superseded_by`, mandatory citation triple, taxonomy edition | Cannot answer the archive's defining question; cannot prevent displaying a superseded threshold as current |
| **D5** | Open question: which single API key to test with | No such question. Tiered router, provider is config, cost metered per call | Restores v1 §7's rule, which the Master Review's stack blueprint regressed by naming specific models |
| **D6** | `PolicyChange.risk_score` with no defined origin | Deterministic versioned table: topic × magnitude × source reliability, unit-tested | A model-produced score cannot be explained to a regulator or reproduced six months later |
| **D7** | Safety gate blocks forbidden phrases | Prose rendered from fixed templates over structured fields; blocklist only as backstop | Blocklists are evaded by paraphrase — "you qualify" passes. Templating makes advice-shaped output unconstructible |
| **D8** | No Alembic migration in the tree, though `alembic` is pinned | Migration from the first table | A schema built on versioned snapshots needs migration discipline before the first production incident |
| **D9** | Slice ends at the public feed endpoint; no dispatcher | Telegram dispatcher in Stage 3, idempotent per notice | The Master Review's own acceptance test ends at "Telegram alert dispatched", so the slice could not pass it. Also Track B's channel |
| **D10** | Tests cover parsers, pipeline, schemas, safety gate | Adds a ~20-document golden corpus as release gate, and recorded-response mode | The only mechanism catching an extraction regression before users do. Also stops the suite billing an API |
| **D11** | Source registry has no health behaviour | Rate limit, timeout, retry, failure count, auto-disable, last-success | Required by v1 §6, cheap at Stage 2, tedious to retrofit |
| **D12** | No backup or restore work in the slice | Restore drill is Stage 6's exit criterion | The archive is the principal asset; untested backups make a volume failure company-ending rather than an outage |
| **D13** | Redis in compose from the start; no queue in code | Redis and worker queue arrive at Stage 4 | Fewer moving parts while the pipeline is deterministic; honest about deferral rather than silently absent |
| **D14** | `POST /admin/approve/{change_id}` | Adds reject-with-reason, reviewer identity, immutable audit on both paths | "All material actions appear in audit logs" is an acceptance criterion; approve-only cannot satisfy it |
| **D15** | No data-protection constraint on the schema | Data minimisation designed in: no case descriptions stored; a lead is an ID + consent record + audit row | NDPA 2023 obligations are unaddressed in all three documents and land on the lead-gen revenue engine |
| **D17** | `Tenant` model plus a tenant key on content rows | Three layers: archive (no tenant), subscription (config), publication (tenant-scoped) | A tenant key on content either duplicates the archive per portal or forces rewriting every query later. It also makes v1 criterion #15 — one source, different tenant outputs — unsatisfiable |
| **D18** | `theme: immigration` as a config string; per-tenant "AI instructions" | Domain pack as versioned, tested code; tenant config holds only a pack reference | Extraction schemas and prompts cannot be free-text tenant config — that is the hallucination surface the Master Review closed. It also separates a cheap new portal from an expensive new vertical |
| **D19** | No provenance for which schema produced a fact | `domain_pack` + `pack_version` stamped on every fact | Same silent-corruption class as the taxonomy edition: you cannot re-extract, compare or invalidate facts without knowing which pack version wrote them |
| **D20** | Tenant implied by the URL path only | Tenant resolved by host from Stage 1; audit rows carry tenant | Each portal is meant to look independent on its own domain. Retrofitting host resolution touches every route and auth check |
| **D21** | Review queue implicitly per published item | Review the *fact* once; publish to N tenants by rule | Otherwise the human queue multiplies per portal and the staffing arithmetic breaks at portal three |
| **D16** | Work begins immediately at the code | Tracks A and B start day one, in parallel | The six clearances are the real critical path, and Track B is the only demand test in the roadmap |

## §7 Five things to settle before Stage 1 — three down

Questions 3 and 4 are answered and absorbed into §3.3 and the data-minimisation rules below.
Question 2 is answered in substance by the §2.2 ladder and needs only a named owner. That leaves
Question 1 as the one decision still genuinely open.

1. **Two lanes, with Lane A shipping before any AI?** *Assumed yes.* The load-bearing decision.
   Reject it and v2 collapses back to roughly the attached plan's ordering, with D4–D16 still applying.
2. **Who owns the Lane B review queue, and do we accept graduated auto-publish?** *Assumed:* the
   §2.2 ladder — Class 1 automatic at launch, Class 2 promoted on 50 clean approvals, Classes 3–4
   held — plus one named reviewer at 4 working hours flagged / 48 routine, with a documented
   fallback. Without a named owner, Stage 5 builds a queue nobody empties, and the failure is silent:
   notices keep firing while interpretation output quietly goes to zero.
3. **Do we store case descriptions in the overstay and lead flow?** — **SETTLED 12 Sep: no.** The
   referral payload reaches the partner and is dropped. Retained: lead ID, route interest,
   destination country, timestamp, consent version, partner routed to, outcome status. The audit log
   records *that* a referral happened, never what it said; request-body logging off on those
   endpoints and error-tracking payloads scrubbed. And if a case description is ever sent to a model
   for triage, that call runs under zero retention — a clean database does not help if the text sat
   in a vendor's logs.
4. **Will any portal ever be operated by someone outside MCS?** — **SETTLED 12 Sep: no, every
   portal is MCS-owned.** Multi-brand single-operator. Deletes row-level security, per-tenant secrets
   and quotas, self-serve onboarding, per-tenant SLAs and the archive licensing question outright —
   see §3.3 for the full list and for the one inference not to draw from it.
5. **Who is building this, at what commitment?** Still unnamed in every document. The 24–31 day
   figure is one competent engineer full-time. Part-time roughly doubles the calendar; the same
   person also running the review queue and partner sales roughly doubles it again.

Confirm Question 1 and name the reviewer, and Stage 1 is buildable immediately: the schema,
migration, storage interface and audit log need no vendor decision, no API key and no Docker.
Question 5 changes only the calendar.
