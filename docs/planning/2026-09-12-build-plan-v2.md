# Portal Build Plan v2

**Date:** 12 September 2026
**Status:** proposed — supersedes the Phase 1 implementation plan
**Baseline:** Master Review + Phase 1 implementation plan. Master Plan v1 is historical reference only.
**Published version:** https://claude.ai/code/artifact/dc28d1e7-7f7f-4474-948c-efdac1b668db
**Companion:** `2026-09-12-third-reading.md`

Same destination as the attached implementation plan, reordered around one structural change:
**the first shippable product contains no AI at all.**

| | |
|---|---|
| **Scope** | UK + Canada only. Tenant key present, tenant tooling deferred |
| **Shape** | 6 build stages each with an exit test, 2 parallel non-engineering tracks |
| **Effort** | 23–30 engineering days to full Lane A + Lane B (one full-time engineer) |
| **First live output** | End of Stage 3 — ~11 days in, zero AI spend |

---

## §1 What carries over intact

v2 is a reordering and a tightening, not a replacement. Kept verbatim from the attached plan:

- The **module layout** — `core / models / schemas / ingestion / pipeline / api`.
- **Config-driven tenants and sources** in YAML, with the tenant FK present from the first table
  while all tenant *tooling* is deferred. The best call in the document: cheap now, agonising to
  retrofit, and no gold-plating.
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

## §3 Two tracks that start before Stage 1

### Track A — Clearances (file all six on day one)

| Item | Gates | Owner |
|---|---|---|
| Managed transactional email, production access | Any email. Accounts start sandboxed/capped; production access can be refused; warm-up follows approval | CTO |
| Domain, DNS, SPF/DKIM/DMARC | Email plus brand. Sending reputation cannot be bought late | CTO |
| Meta business verification → WhatsApp Cloud API | The paid alert tier. Needs verified entity and documents | Tunde |
| Paystack / Flutterwave merchant onboarding | All revenue. Needs CAC registration and compliance review | Tunde |
| 3–5 licensed legal partners under contract | Primary revenue engine. Longest lead time — enterprise sales with legal negotiation | Tunde |
| Data-protection position (NDPA 2023) | Lead gen and user accounts. Determines what may be collected → determines the schema, so it gates **Stage 1** | Tunde + counsel |

### Track B — Manual validation (no code)

- **Run Lane A by hand, now.** Telegram channel, UK/Canada updates posted manually in the notice
  format, two weeks. Tests whether an audience forms, reveals from the replies which fields people
  actually ask about, and seeds the distribution list Stage 3 then takes over.
- **Sell five dossiers by hand.** Bank transfer, hand-written PDF. Five sales is a real
  willingness-to-pay signal; zero is the most valuable finding available, at a cost of two days.

Writing five dossiers manually tells you which extraction fields matter far better than designing
the Pydantic schema in the abstract — Track B is a genuine input to Stage 4.

## §4 The build, stage by stage

Sequenced by dependency, sized in engineering days for one competent full-time engineer.

### Stage 1 — Spine · 3–4 days
- This repository. Alembic migration from the first table.
- Temporal fact schema (§4.1): `valid_from`, `valid_to`, `superseded_by`, citation triple, taxonomy edition.
- `ObjectStore` interface — local FS now, R2 later. Postgres never holds raw bytes.
- `AuditLog` on every state transition, append-only, with actor identity.
- `tenants.yaml` / `sources.yaml` validated at startup; tenant FK on every content row.

**Exit test:** migration clean on Postgres *and* SQLite; a snapshot lands as bytes on disk with only
hash/pointer/metadata in the DB and one audit row; persisting a fact without a resolvable citation
triple raises.

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
- Approved interpretation attaches to its notice and dispatches a follow-up.

**Exit test:** a historical UK threshold change replays end to end — notice fires immediately,
interpretation quarantines, a named reviewer approves, follow-up dispatches, prior fact marked
superseded with a pointer, every step reconstructable from the audit log alone. Reject path verified.

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

### §4.1 The record every stage is built around

```
policy_fact
  tenant_id        fk              # present from stage 1, unused until later
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
```

Three fields separate an archive from a news feed. The **validity interval and supersession pointer**
answer *"what did this rule say on 14 March 2024"* — the only question a competitor polling the same
public API cannot answer. The **citation triple** ties every claim to the exact bytes seen. The
**taxonomy edition** prevents silent corruption in year two: UK SOC and Canadian NOC both get
revised, codes get reused with changed meanings, and an unstamped mapping starts returning wrong
occupations with no error anywhere.

## §5 Divergence from the attached implementation plan

D1–D4 are structural and the rest follow from them; D5–D16 are independent and can be taken
piecemeal.

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
| **D16** | Work begins immediately at the code | Tracks A and B start day one, in parallel | The six clearances are the real critical path, and Track B is the only demand test in the roadmap |

## §6 Four things to confirm before Stage 1

v2 assumes the answers below. Three of the four change the schema, so they are cheap now and
expensive at Stage 4.

1. **Two lanes, with Lane A shipping before any AI?** *Assumed yes.* The load-bearing decision.
   Reject it and v2 collapses back to roughly the attached plan's ordering, with D4–D16 still applying.
2. **Who owns the Lane B review queue, and what is the response target?** *Assumed:* one named
   reviewer, 4 working hours flagged / 48 routine, documented fallback. Unanswered, Stage 5 builds a
   queue nobody empties — a pipeline that silently publishes nothing.
3. **Do we store case descriptions in the overstay and lead flow?** *Assumed no* — encrypted to the
   partner, never retained; we keep an ID, a consent record and an audit row. Constrains the Stage 1
   schema, so it cannot wait for the lead product.
4. **Who is building this, at what commitment?** Still unnamed in every document. The 23–30 day
   figure is one competent engineer full-time. Part-time roughly doubles the calendar; the same
   person also running the review queue and partner sales roughly doubles it again.

Confirm 1–3 and Stage 1 is buildable immediately: the schema, migration, storage interface and audit
log need no vendor decision, no API key and no Docker. Question 4 changes only the calendar.
