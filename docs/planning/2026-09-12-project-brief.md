# MCS Information Cloud — Project Brief

**Date:** 12 September 2026
**Status:** pre-build, one decision outstanding
**Published version:** https://claude.ai/code/artifact/9393c542-54d5-446f-a731-45ba7c500483
**Detail:** `2026-09-12-build-plan-v2.md` · **Review:** `2026-09-12-third-reading.md`

A monitoring platform that watches official immigration sources, records exactly what changed and
when, and publishes it to focused consumer portals within seconds of publication — **with every claim
traceable to the government document it came from.** One codebase and one archive behind any number
of independently branded portals.

---

## The problem

Nigerian and West African migration demand is enormous and urgent, and the information environment
serving it is actively harmful: rumour on TikTok and WhatsApp, predatory "ghost" consultants, and
government rules that shift without warning. People make irreversible, expensive decisions —
thousands of pounds in non-refundable fees, life savings, sometimes their legal status — on the basis
of a stranger's video.

Nobody is offering the boring thing that actually helps: **an accurate, timestamped, cited record of
what the rules say and when they changed.** That is the product.

## How it works

| | Step | |
|---|---|---|
| 01 | **Collect from official sources only** | GOV.UK Content API and IRCC feeds — structured, public, no scraping, no bot fights. UK + Canada at launch |
| 02 | **Archive the bytes, detect real change** | Document stored whole in object storage; SHA-256 compared against the last version. Identical content discarded, so nothing downstream runs on a non-event |
| 03 | **Publish the notice** — *Lane A, automatic* | Authority's headline, official link, retrieval timestamp, content hash. No interpretation, therefore near-zero legal exposure, out the door in seconds. **No AI involved at all** |
| 04 | **Extract, compare, interpret** — *Lane B, gated* | Structured facts into a strict schema, compared against the previous version, risk-classified by a deterministic table |
| 05 | **Review only what can cause harm** — *Lane B, gated* | Routine restatements publish themselves. Salary thresholds, quota cutoffs and anything touching overstay go to a person first. The gated set shrinks as accuracy is measured |
| 06 | **Distribute per portal** | Telegram, WhatsApp, email, and each portal's own website — every item carrying its citation, retrieval time and that portal's disclaimer |

**The one design choice everything follows from:** splitting the fast, safe fact ("this document was
published, here it is") from the slow, risky interpretation ("here is what it means for you"). It lets
us promise *instant* alerts and still put a human in front of anything that could cost someone an
application — because those are no longer the same object.

## What we are actually building

- **One system, many portals.** One backend, one frontend codebase, one database, one deployment. A
  portal is a block of YAML, a DNS record and its own channel identities — not an application. Adding
  one takes hours.
- **One shared archive.** The policy history is stored once and consumed by every portal. A second
  portal costs nothing extra to feed, and each new portal makes the archive more valuable.
- **Subject packs are code.** Immigration is pack #1: its schemas, prompts, risk rules and templates.
  A new portal in a covered subject is configuration. A new *subject* is a new pack and real engineering.
- **Every fact is dated.** Facts carry validity ranges and supersession pointers, so we can answer what
  a rule said on any past date — and can never show a superseded threshold as current.

First two portals: **VisaTrack Africa** (immigration information and policy monitoring) and
**SkilledPath Africa** (trades and skilled-worker migration). Both MCS-owned, both drawing on the same
archive, neither showing any sign of the other or of the platform underneath.

## Why it is defensible

Polling a public API is not a business. Three things compound and cannot be copied quickly:

- **The time-series archive.** The ability to answer *"what did this rule say on 14 March 2024, and
  which document says so"* for African-relevant corridors. It starts accruing on day one and nobody
  else is keeping it. Also a product in itself: historical data and API access for lawyers and researchers.
- **The distribution list.** Telegram and WhatsApp opt-ins — direct, portable, not at the mercy of
  anyone's algorithm.
- **The vetted partner network.** Licensed immigration solicitors and consultants under contract. Slow
  to build, slow to copy, and the main revenue engine.

Because the archive is the principal asset, backup integrity is a business concern rather than an
infrastructure detail: off-provider backups, append-only hash-chained snapshots, and a documented
restore drill inside the initial build.

## How we stay on the right side of the law

- **Information, never advice.** Published prose is rendered from fixed templates over structured
  fields, so advice-shaped phrasing cannot be constructed — not merely blocked by a word list that
  paraphrase defeats.
- **Citation or no publication.** Every fact carries a URL, a retrieval timestamp and a hash of the
  archived bytes. Publishing without a resolvable citation is structurally impossible.
- **No incriminating data held.** In the legal-referral flow the case description reaches the partner
  and is dropped. We keep an ID, a consent record and an audit row — never a written admission tied to
  a person.
- **Claims, not people.** Fact-checking addresses the claim and never accuses an individual, with right
  of reply and a correction trail. This is why social verification is deferred rather than rushed.

## The build — 7 stages, 29–38 engineering days

| Stage | Delivers | Days |
|---|---|---|
| 1 · Spine | Repository, migrations, the three data layers, dated-fact schema, storage interface, audit log | 4–5 |
| 2 · Ingest | GOV.UK and IRCC adapters, source health and auto-disable, hash-based change detection. No AI | 4–5 |
| **3 · Lane A** | **First live product.** Notices to Telegram and a public feed, seconds after the source changes, zero AI spend | 3–4 |
| 4 · Extraction | Provider-agnostic model router, strict schemas, a 20-document accuracy corpus, per-item cost metering | 5–7 |
| 5 · Lane B | Version diffing, deterministic risk classes, review queue, and the ladder that automates classes as they prove out | 5–6 |
| 6 · Durability | Object storage, off-provider backups, immutable snapshots, and a restore drill actually performed | 3–4 |
| **7 · Portals** | One website codebase serving every portal on its own domain and branding, built for search visibility | 5–7 |

**Two tracks run alongside from day one, and neither is engineering.** *Clearances:* email production
access, domain and DNS, Meta business verification for WhatsApp, payment-gateway onboarding, three to
five licensed legal partners under contract, and the data-protection position. These are multi-week
queues with real rejection rates, and they — not the code — are the critical path. *Validation:* run
the notice channel by hand for two weeks and sell five dossiers manually, to find out whether the
audience and the willingness to pay exist before ten weeks of engineering are sunk.

## What it costs to run

| | |
|---|---|
| Monthly run-rate | ~$100 all-in, pilot scale |
| Break-even | 1 legal referral per month, or ~15 dossier sales |
| Per policy change | <$0.03 AI cost target |

Infrastructure is not the constraint and never will be at this stage. The scarce resources are
**editorial attention** for the review queue and **signed licensed partners** for the revenue engine —
neither buyable with compute, both with long lead times. That is why partner acquisition sits in week
one rather than week eight.

## Where things stand

| Decision | Status | Note |
|---|---|---|
| Every portal is MCS-owned | **Settled** | Multi-brand single-operator, not SaaS. Removes tenant security isolation, per-tenant secrets and quotas, self-serve onboarding and per-tenant SLAs from scope entirely |
| No case descriptions stored | **Settled** | The referral payload reaches the partner and is dropped. Audit rows record that a referral happened, never what it said |
| Automation is earned, not assumed | **Settled** | Routine restatements publish automatically from launch; comparative changes promoted once a class proves out; overstay and unlawful presence never auto-publish. Expected destination 80–90% automatic within months |
| Confirm the two-lane model | **Open** | The last load-bearing decision. Yes means a live product in ~12 days with no AI spend; no means one pipeline and ~25 days to first output |
| Name the review-queue owner | **Open** | One person, 4 working hours flagged / 48 routine, written fallback. 1–7 hours a week at launch scope. Without a name the queue fills and the failure is silent |
| Who is building it | Affects calendar only | Day figures assume one competent engineer full-time. Part-time roughly doubles the calendar; one person also running the review queue and partner sales roughly doubles it again |

## Not in this build — deliberately

Social-media claim verification and all inbound social monitoring; automated posting to X, Facebook
and Instagram; payments; the B2B lead flow itself; SkilledPath's trade taxonomy content; and any
portal-management console. Countries beyond the UK and Canada are out too — each additional country
multiplies review effort, the one cost that does not scale for free.

Each is straightforward to add once the spine exists, and each is gated on the validation track showing
there is an audience worth serving.

> Figures and legal positions in this document require verification before operational use.
