# MCS Portal — Third Reading

**Date:** 12 September 2026
**Reviews:** `MCS_Automated_Information_Portal_Master_Plan_v1.md`, `mcs_platform_master_review.md`, `implementation_plan.md`
**Repository state at time of writing:** empty, no commits
**Published version:** https://claude.ai/code/artifact/7a76f550-2388-425c-8f79-a267f4e734f5

---

## Verdict

The business thesis holds. The Master Review's engineering redesign is close to right and
should be adopted. The unresolved problem is **governance**: the Review has become the de facto
architecture while the Master Plan is still the contract, and the two contradict each other in
writing. Resolve that before the first commit.

## §1 — Governance defect (BLOCKING)

v1 §18's 21 acceptance criteria are still the stated definition of pilot-ready, but the Review
invalidates several. Build to the Review and the CTO fails on paper; build to v1 and they ship the
failures the Review predicted.

| Criterion | Conflict | Replace with |
|---|---|---|
| #16 self-hosted mail subsystem | Review §2.1 kills self-hosted SMTP | Deliverability measured, not owned: ≥99% accepted, bounce <2%, complaint <0.1%, provider swappable behind one adapter |
| #9 high-confidence auto-publishes | Review inserts HITL gate | Split by lane (§2.2): notices auto-publish, interpretation gated |
| #11 users receive matching alerts | Channel priority inverted — Telegram/WhatsApp now Tier 1 | Delivered on elected channel; email is fallback |
| #13 social claims investigated | Review §3.3 adds defamation constraints v1 lacks | Add: no named individual, right of reply logged, correction trail, takedown SLA |
| #3 source added via admin console | Impl. plan uses YAML, not a console | Source added by config change without app redeploy; console deferred to Phase 5 |

Criteria 1, 2, 4–8, 10, 12, 14, 15, 17–21 survive intact.

**Fix:** declare the Master Review normative on architecture, sequencing and channels; v1 normative
on business scope, tenancy, acceptance criteria and security posture as amended above; the
Implementation Plan subordinate to both. Commit the hierarchy as the first commit.

## §2 — Where I part company with the Master Review

**2.1 It hardcodes model names.** v1 §7 got this right ("model names must be configuration
values"); the Review's stack blueprint regressed it and already cites stale model generations.
Keep the two-tier idea (fast extractor / strong reasoner), discard the names. Tier is
architecture; model is config with a recorded cost and accuracy score.

**2.2 The human gate is unstaffed and contradicts the product promise.** No owner, no SLA, and
v1 §15 says Tunde gets only strategic alerts. It also collides with the paid *instant* alert.
Resolve with two lanes:
- **Lane A — Notice (automatic, seconds):** authority's headline, official URL, retrieval
  timestamp, document hash. Zero interpretation, therefore minimal regulated-advice exposure.
  This is what fires Telegram/WhatsApp.
- **Lane B — Interpretation (gated, hours):** what changed, who it affects, prior value. This is
  where liability lives and the only thing needing a human.

Then staff Lane B: one named reviewer, 4 working hours for flagged / 48 for routine, documented
fallback. Tier 1 scope implies ~5–20 gated items/week — one part-time person. That breaks the
moment a third country is added, which is the real argument for the tiered model.

**2.3 The legal analysis is aimed at the wrong jurisdiction.** OISC/CICC/UPL reach over a
Nigerian company publishing to Nigerian users is likely narrower than the Review implies (the UK
regime attaches to advice provided in the UK). Worth one paid hour of a UK solicitor's time to
establish. Meanwhile **nothing in three documents mentions Nigerian data protection.** The plan
collects nationality, occupation, education, family relationships, travel intent and — in the
overstay flow — admissions of immigration violations, then transfers them to third-party firms,
some abroad. Under the Nigeria Data Protection Act 2023 that engages lawful basis, registration,
DPO and cross-border transfer obligations with the NDPC as regulator; add UK/EU GDPR if any
UK/EU user touches the service. This lands directly on the revenue engine.

**2.4 The lead-gen model needs an ethical floor.** Pay-per-lead rewards volume regardless of
outcome — the exact incentive that produces the "ghost consultants" the platform opposes. Three
cheap constraints: (a) do not store the confession — case description goes to the partner
encrypted, retain only a lead ID, consent record and audit entry; (b) verify partner licences
continuously against the public register, auto-suspend on lapse, publish vetting criteria;
(c) price for placement (retainer or capped rate with quality clawback), never uncapped per-lead.

## §3 — Three gaps neither document covers

**3.1 The archive is the moat, so backup integrity is a business concern.** Ingesting public APIs
is not defensible. Three things are: the time-series archive (what did this rule say on
14 March 2024, and from which document), the distribution list, the partner network. Consequence:
a corrupted Postgres volume with untested backups is loss of the principal asset, not an outage.
v1 says only "backups stored separately" and Contabo offers no managed database. Require stated
RPO/RTO, off-provider backup destination, append-only hash-chained snapshots, and a **restore
drill executed and documented in Phase 1** — not Phase 6.

**3.2 There is no demand test anywhere in 14 weeks.** First revenue is Week 8; everything before
is build. Insert a Week 0 costing nothing: open the Telegram channel now and post UK/Canada
updates by hand in Lane A format for two weeks (tests audience, teaches you what they ask for,
seeds the distribution list); sell the dossier manually in Week 3 by bank transfer with a
hand-written PDF. Five sales is a real signal; zero is the most valuable finding in the plan.
Manual fulfilment also teaches the extraction schema better than designing it in the abstract.

**3.3 The critical path is paperwork, not code.** Every revenue-bearing channel in Phases 3–4
sits behind a multi-week third-party approval with a real rejection rate, none listed as a
dependency:

| Dependency | Blocks | Why not a Week-8 task |
|---|---|---|
| Managed-SMTP production access | All email | Accounts start sandboxed/capped; production access can be refused; warm-up follows approval |
| Domain, DNS, SPF/DKIM/DMARC | Email, brand | Propagation plus reputation build — cannot be bought late |
| Meta business verification, WhatsApp Cloud API | Paid alert tier | Needs verified business entity and documents; weeks |
| Paystack / Flutterwave merchant onboarding | All revenue | Needs CAC registration and compliance review |
| 3–5 licensed legal partners under contract | Primary revenue engine | Enterprise sales with legal negotiation; longest lead time in the plan |
| Data-protection posture (§2.3) | Lead gen, user accounts | Determines what may be collected, which determines the schema |

File all six in Week 0. The 14-week plan is roughly 2× optimistic *on the calendar* while about
right *on the engineering* — the entire gap is these six queues.

## §4 — Corrections to the Phase 1 slice

The Implementation Plan is the strongest of the three as engineering, and keeping the tenant
foreign key while deferring all tenant *tooling* is exactly right. Eight corrections, in
descending order of cost-to-fix-later.

**4.1 Every fact needs a validity interval and a supersession pointer.** The schemas carry
`effective_date` and stop. That cannot answer the question the archive exists to answer, and
cannot stop you displaying a superseded threshold as current — the most likely way this platform
harms a user. Minimum publishable record:

```
policy_fact
  route            "uk.skilled_worker"
  field            "general_salary_threshold"
  value            { amount, currency }
  valid_from       date            # not "effective_date"
  valid_to         date | null     # null = current, set on supersession
  superseded_by    fact_id | null
  taxonomy         { scheme: "SOC", edition: "2020" }
  citation
    url            official source URL
    retrieved_at   timestamp
    content_sha256 hash of the archived bytes
  confidence       float
  risk_tier        enum, deterministic (4.5)
```

The **citation triple** (URL + retrieval time + hash of archived bytes) makes every claim
traceable to the exact document seen — your defence in a dispute. Make publishing without one
structurally impossible. The **taxonomy edition** field prevents silent corruption in year two:
UK SOC and Canadian NOC both get revised, codes are reused with different meanings, and a mapping
without an edition stamp starts returning wrong occupations with no error anywhere.

**4.2 Raw payloads belong in object storage, not Postgres.** `ContentSnapshot` storing raw
payload contradicts the Review's own §2.4. Bytes to R2; hash, pointer and metadata in Postgres;
both behind one storage interface with a local-filesystem implementation for development.
Otherwise the primary database becomes an HTML landfill and backups become unusable — see §3.1.

**4.3 Build the model router in the slice; never let tests call a paid API.** The slice has no
provider abstraction and its open question asks which single API key to use. Wrong shape: the
provider is config (v1 §7, §2.1 above). Build the tier-based router now and give it a
recorded-fixture mode so tests replay saved responses.

**4.4 A golden fixture corpus is the highest-value test asset.** No regression corpus exists in
the verification plan. Build ~20 real historical policy documents with hand-verified expected
extractions, run on every prompt/model/schema change. Treat a drop in pass rate as a release
blocker. It is the only mechanism that catches extraction regressions before users do.

**4.5 Risk score must be deterministic.** `PolicyChange.risk_score` has no defined origin. If a
model produces it you cannot explain a routing decision or reproduce it later. Make it a table:
topic class × magnitude × source reliability, in code, versioned, unit-tested. Anything touching
salary thresholds, quota cutoffs, overstay or unlawful presence routes to Lane B regardless.

**4.6 Template the output prose instead of blocklisting phrases.** Blocklisting "you are
eligible" / "we guarantee" is trivially evaded by paraphrase ("you qualify", "your profile meets
the requirement"). Invert it: render published prose from fixed templates populated by structured
fields, so advice-shaped phrasing is unconstructible rather than forbidden. Keep the blocklist as
a backstop on any remaining free-text path.

**4.7 The slice cannot pass its own Week 4 acceptance test.** The Review's vertical slice and the
30-day plan both end at "Telegram alert dispatched"; the Implementation Plan stops at a feed
endpoint with no dispatcher. Add a minimal Telegram publisher (small, and also the Week 0 channel
from §3.2) or amend the acceptance test. Do not discover this in Week 4.

**4.8 Put the code in this repository, and write the migration from commit one.** The plan targets
a scratch directory on a Windows laptop. A platform whose value is an immutable audit trail should
not begin outside version control. `alembic` is in requirements but no migration is in the file
tree. Also: ingestion is synchronous behind `POST /ingest/run` with no queue — fine for a slice,
but state it as a deliberate deferral since the Review's architecture rests on one. And v1 §6
requires rate limiting, retry, failure counting and automatic source disabling, none of which
appear in the slice; source health is cheap early and tedious to retrofit.

## §5 — What this costs to run

At pilot scale on the Review's own figures: **~$100/month all-in**. Break-even is **one B2B legal
lead per month**, or ~15 dossier sales. The Review's <$0.03 per policy change target is sound.
Verify against current provider pricing, but the order of magnitude is the point: **infrastructure
is not the constraint and never will be at this stage.**

Therefore the optimisation effort is misallocated. Considerable attention goes to shaving VPS and
token costs; comparatively little to the two genuinely scarce things — **editorial attention** for
Lane B and **signed licensed partners** for the revenue engine. Neither can be bought with
compute; both have long lead times; both are currently someone's Week 8 problem. Move engineering
ambition down a notch and partner acquisition to first position.

## §6 — Six decisions that are not the CTO's

The Implementation Plan's open questions (which API key, is Docker installed) are engineering
details. These six block or reshape Phase 1:

1. **Who owns the Lane B review queue, and what is their response target?** Unanswered, the safety
   architecture is decorative. *Recommend:* one named reviewer, 4 working hours flagged / 48
   routine, documented fallback.
2. **Do we accept two-lane publishing?** The only way I see to keep the instant-alert promise and
   the human gate in one product. *Recommend:* adopt, rewrite criterion #9 around it.
3. **What is our data-protection position before the first lead is sold?** Lawful basis, retention,
   cross-border transfer, and whether case descriptions are stored at all. *Recommend:* they are
   not — §2.4.
4. **Do we run Week 0 before Phase 1?** Two weeks, no code, retires the largest unpriced risk and
   seeds distribution. *Recommend:* yes, and start the six administrative queues the same day.
5. **Is the Master Review normative, and is v1 §18 amended?** The CTO cannot resolve a conflict
   between two documents you own. *Recommend:* adopt the §1 hierarchy and commit it.
6. **Who is doing this, and at what commitment?** Never named in three documents. 14 weeks is
   plausible for one full-time engineer with paperwork running in parallel; not part-time, and not
   if the same person also runs the review queue and partner sales.

---

## Summary

The thinking is good and further along than most projects at this stage. The Master Review did the
hard work of killing what would have failed; the Implementation Plan is competent engineering.
What is missing is not more analysis — it is closing the three documents into one normative
decision, staffing the human gate already designed, starting the administrative clocks, and
finding out in the next fortnight, for free, whether anyone wants this. Then build the slice, in
this repository, with dated facts and traceable citations.

> Figures and legal positions in this document require verification before operational use.
