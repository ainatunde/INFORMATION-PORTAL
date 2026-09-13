# Fourth Reading — independent verification at commit `8327df2`

**Date:** 13 September 2026
**Repo reviewed:** `ainatunde/mcs-platform` @ `8327df2` (cloned, installed, executed)
**Published version:** https://claude.ai/code/artifact/00e299c8-d34d-49b9-843f-c5930539b7b5
**Probes:** `probes/test_independent_probes.py`, `probes/migration_backfill_probe.py`

Unlike the previous rounds, this was executed against the code rather than read off a report.
**The remediation is largely real** — six of the ten previously reproduced blockers are genuinely
closed. Four defects survive, three walkthrough claims describe code that does not exist, and one
item the walkthrough never mentions is the most urgent thing here.

| | |
|---|---|
| Suite re-run independently | **37/37 passed in 7.53s** — matches the walkthrough |
| Blockers closed | 6 of 10, verified in code |
| Still open | 4, reproduced by probe |
| Walkthrough claims contradicted by code | 3 |

## ⚠ Before anything else: the repository is public

Nothing secret is committed — `.gitignore` covers `.env`, and `git ls-files` shows no env file — so
this is not a breach. But make it private now. It is a policy platform with an operator credential
model and a runbook naming live API keys, and the sanctioned credential string
`test-operator-key-valid` is world-readable alongside the logic that accepts it.

## Genuinely fixed (verified in code)

| Finding | Evidence |
|---|---|
| **F01 auth** | `secrets.compare_digest` is real. Outside `ENVIRONMENT=="test"` the test key cannot authenticate; a default or test-valued `OPERATOR_API_KEY` raises 500. `ENVIRONMENT` defaults to `"development"`, so a deploy that forgets to set it fails **closed**. The reproduced bypass is gone. |
| **F04 providers** | `grep -rn NotImplementedError` returns nothing. Real `httpx` adapters hit `generativelanguage.googleapis.com`, `api.openai.com`, `api.anthropic.com`, each raising if its key is unset. |
| **F06 promotion** | `can_auto_publish_async` reads the DB. Class 3/4 are hard `return False` before any counter; `is_unmapped` likewise. Probe passed 10,000 approvals — none promoted. |
| **F07 storage** | `boto3>=1.34.0` declared and installs. `r2://bucket/` prefix stripped before the S3 call, so write/read round-trips. |
| **F08 migration** | Migration 002 **does** backfill. Built a populated pre-002 DB, upgraded, ran the runtime verifier: `ok=True`. Backfilled history is verifier-consistent. |
| **F12 predecessor** | `status == "active"` + `.limit(1)` + `scalar_one_or_none()`. `MultipleResultsFound` path gone. |
| **F15/F16 frontend** | `JSON.stringify(jsonLd).replace(/</g,'\\u003c')` neutralises the `</script>` breakout; loader returns `{ notFound: true }`. |

## Still broken (my probes, not the implementer's)

The eight probes in the suite were written by the person fixing the defects and grade their own
work, which is why they all pass.

**1. The evidence gate accepts empty evidence — P1.** The citation constraint only tests
`IS NOT NULL`; an empty string is not null.

```
[FAIL] A: empty citation_url + bogus sha256 persists
    persisted=True; url='' sha256='not-a-real-digest' (len 17, expected 64)
```

This defeats "citation or no publication", the guardrail the legal posture rests on. Their
`test_mandatory_citation_triple` misses it — passes `citation_sha256="abc"` but only asserts the
*null* URL raises, and catches bare `Exception`.
*Fix:* constrain `length(citation_sha256)=64` + hex pattern, non-empty scheme-checked URL, one
assertion per field.

**2. Reviewer attribution does not exist — P1, and it breaks the plan.**

```
[FAIL] D: reviewer attribution distinguishes individuals?
    every authenticated caller becomes reviewer_id='operator_lead_editor'
    role='admin' scopes=6; no per-person key
```

One shared key; `get_current_operator` returns a hardcoded identity. The previous review asked
whether `reviewer_id` could be *forged* — it can't any more, because there is only one identity to
forge. Audit rows cannot say who approved anything, individuals cannot be revoked, and
`require_scope` is dead code (`role == "admin"` short-circuits).

**Why this is a plan failure:** Stage 5's exit criterion is an audit trail carrying *reviewer
identity*, and the ladder promotes on *fifty clean approvals by a named reviewer*. With a shared
key both reduce to "somebody with the password".

**3. Chain truncation undetectable in practice — P1.**

```
[FAIL] C: full_chain_ok=True; after_removing_newest_ok=True
$ grep -rn "expected_tip_hash" app/ | grep -v hash_chain.py
    (no production caller supplies a trusted tip)
```

Implementing the parameter without persisting a checkpoint closes nothing.
*Fix:* persist the tip after each append to a different failure domain; refuse to pass without one.

**4. The outbox worker is written but never runs — P1.**

```
$ grep -rn "OutboxWorker" app/ tests/
app/pipeline/outbox_service.py:142:class OutboxWorker:
```

Lease claiming and exponential backoff exist as a class referenced nowhere else in the repository.
Delivery is still immediate-send plus the manual endpoint.

## Walkthrough claims the code contradicts

1. **"`app/templates` autoescape enabled in Jinja2"** — no such directory, no Jinja2 import in
   `app/`. Rendering is `html.escape` in `app/web/portal_renderer.py`, which is what required
   correction 9 asked the document to say. `jinja2` is in requirements but nothing imports it.
2. **"Asynchronous background task with concurrency lock … orphan recovery on startup"** — none of
   the three exist. No `BackgroundTasks`, `add_task`, `asyncio.Lock` or `Semaphore` anywhere in
   `app/`. `lifespan` loads two config files and yields. Orphan recovery is a *request parameter*
   (`recover_orphans: bool = True`) — exactly what correction 3 said to write instead.
3. **The document contradicts itself in fifteen lines.** Line 4 says "production acceptance
   blocked" (correct, adopted). Line 18 says "All placeholder implementations … have been
   eliminated" — the sentence correction 1 asked to remove, retained and strengthened, and false
   given the four findings above.

**The distinction worth holding on to:** some re-asserted claims could have become true through
later work, and several did. But claims about *what the original defect was* cannot be fixed by new
code — and F02's description was rewritten from "AsyncSession lazy loading" to "unbounded
synchronous crawl", F08's from "checked output length" to "compared index against itself", and F11
relabelled P2 after the review explicitly said not to. When a report edits history to match the fix
it wants to claim, it stops being evidence.

## Against build plan v2

| Plan item | State | Note |
|---|---|---|
| Three layers, tenant-agnostic archive | ✅ Built | `test_factory_test_one_fact_two_tenants`, host-based tenant resolution |
| Subject-agnostic naming | ✅ Built | `subject_pack`, `pack_version`, `topic` are the real field names |
| D5 model-name independence | ✅ Built | `test_stage4_model_name_independence`; provider is config |
| Class 4 un-promotable in code | ✅ Built | Hard `return False` before any counter — exactly our exit test |
| Stages 1–7 present | ✅ Built | A test module per stage, plus Next.js portal and SEO route |
| D2 code in version control | ✅ Done | Satisfied by this repo — make it private |
| Citation or no publication | ❌ Not enforced | Probe 1 |
| Reviewer identity in audit trail | ❌ Not enforced | Probe 2 |
| Off-provider backup, stated RPO/RTO | ⚠ Partial | Backup writes to local `backups/`; Stage 6 required a different failure domain |
| Track A — six clearances | ❌ No evidence | The real critical path; should have started day one |
| Track B — manual demand validation | ❌ No evidence | Still no test of whether anyone wants this |
| Scope discipline | ✅ Held | No Verify, payments, lead flow or tenant console — nothing out of scope built |

Scope discipline deserves credit: seven stages built, nothing built that we agreed to defer. The gap
is not scope creep — it is that **both non-engineering tracks appear not to have started**, and
those were always what stood between this and a live product.

## What to do, in order

1. **Make the repository private.** Minutes, and the only item with external blast radius.
2. **Per-operator credentials.** Until an approval can be attributed to a person, the audit trail is
   decorative and the promotion counter measures an anonymous key. Blocks trusting the ladder.
3. **Tighten the evidence constraint** — hex/length digest check, non-empty scheme-checked URL, one
   assertion per field.
4. **Start the outbox worker** and **persist a chain checkpoint.** Both small: the machinery exists
   in each case and simply is not wired up or supplied.
5. **Correct the walkthrough from the code**, not from the previous draft.
6. **File the six Track A clearances this week.** They take weeks; no code shortens them.

> **On process, not code.** Three rounds have followed the same shape: a confident completion
> report, then a probe that contradicts it. The code is improving quickly and genuinely. What keeps
> failing is the reporting. Stop treating a narrative document as status: make the status the tests,
> require that probes for a finding are written by someone other than whoever fixed it, and never
> let a summary line assert more than the findings below it support.

**Not verified:** live providers, real R2, Telegram delivery, PostgreSQL, multi-process concurrency,
browser behaviour, Lighthouse.
