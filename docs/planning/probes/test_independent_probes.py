"""Independent probes written by the reviewer, not the implementer."""
import pytest, pytest_asyncio
from datetime import date, datetime, timezone, timedelta

from app.core.database import AsyncSessionLocal
from app.models import PolicyFact, ContentSnapshot
from app.pipeline.hash_chain import HashChainValidator, canonical_iso
from app.pipeline.risk_engine import GraduatedAutoPublishTracker

RESULTS = []

def rec(name, outcome, detail):
    RESULTS.append((name, outcome, detail))
    print(f"\n[{outcome}] {name}\n    {detail}")

@pytest.mark.asyncio
async def test_probe_A_empty_string_citation_is_accepted():
    """Evidence gate: nullable=False + IS NOT NULL does not stop an EMPTY citation."""
    async with AsyncSessionLocal() as session:
        fact = PolicyFact(
            subject_pack="immigration", pack_version="1.0.0",
            topic="uk.skilled_worker", field="general_salary_threshold",
            value={"amount": 38700, "currency": "GBP"},
            valid_from=date(2024, 4, 4),
            citation_url="",                  # empty, not null
            citation_retrieved_at=datetime.now(timezone.utc),
            citation_sha256="not-a-real-digest",   # 19 chars, not a sha256
            risk_tier="Class 2", lane="interpretation",
        )
        session.add(fact)
        await session.commit()
        await session.refresh(fact)
        persisted = fact.id is not None
    rec("A: empty citation_url + bogus sha256 persists",
        "FAIL (evidence gate open)" if persisted else "PASS",
        f"persisted={persisted}; url={fact.citation_url!r} sha256={fact.citation_sha256!r} "
        f"(len {len(fact.citation_sha256)}, expected 64)")
    assert persisted, "probe expected the weak constraint to allow this"

@pytest.mark.asyncio
async def test_probe_B_class_3_and_4_never_promote():
    t = GraduatedAutoPublishTracker(promotion_threshold=50)
    out = {}
    for cls in ("Class 1", "Class 2", "Class 3", "Class 4"):
        out[cls] = t.can_auto_publish(cls, consecutive_approvals=10_000)
    unmapped = t.can_auto_publish("Class 2", consecutive_approvals=10_000, is_unmapped=True)
    ok = out["Class 3"] is False and out["Class 4"] is False and unmapped is False
    rec("B: Class 3/4 + unmapped un-promotable at 10,000 approvals",
        "PASS" if ok else "FAIL",
        f"{out}, unmapped_class2={unmapped}")
    assert ok

@pytest.mark.asyncio
async def test_probe_C_tail_truncation_without_checkpoint():
    """Removing the newest snapshot leaves a self-consistent chain."""
    async with AsyncSessionLocal() as session:
        base = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
        snaps, prev = [], None
        for i in range(3):
            idx, prev_hash = HashChainValidator.link_next_snapshot(
                prev, content_sha256=f"{i:064x}", byte_size=100 + i,
                retrieved_at=base + timedelta(hours=i))
            s = ContentSnapshot(
                source_id="src-probe", content_sha256=f"{i:064x}",
                storage_pointer=f"snapshots/src-probe/{i:064x}.bin",
                byte_size=100 + i, retrieved_at=base + timedelta(hours=i),
                chain_index=idx, prev_hash=prev_hash)
            snaps.append(s); prev = s
        full_ok, full_err = HashChainValidator.verify_chain(snaps)
        trunc_ok, trunc_err = HashChainValidator.verify_chain(snaps[:-1])
    rec("C: tail truncation detected without a trusted tip?",
        "FAIL (undetectable in practice)" if trunc_ok else "PASS",
        f"full_chain_ok={full_ok} err={full_err!r}; after_removing_newest_ok={trunc_ok} err={trunc_err!r}; "
        f"no production caller passes expected_tip_hash")
    assert full_ok, f"a well-formed chain must verify: {full_err}"

@pytest.mark.asyncio
async def test_probe_D_reviewer_identity_is_a_shared_singleton():
    """Anyone holding the single API key IS 'operator_lead_editor'."""
    from app.core.auth import get_current_operator
    import os
    os.environ["ENVIRONMENT"] = "test"
    a = await get_current_operator(x_api_key="test-operator-key-valid", authorization=None)
    b = await get_current_operator(x_api_key="test-operator-key-valid", authorization=None)
    same = (a.reviewer_id == b.reviewer_id == "operator_lead_editor") and a.role == "admin"
    rec("D: reviewer attribution distinguishes individuals?",
        "FAIL (single shared identity)" if same else "PASS",
        f"every authenticated caller becomes reviewer_id={a.reviewer_id!r} role={a.role!r} "
        f"scopes={len(a.scopes)}; no per-person key, so audit rows cannot name who approved")
    assert same

def test_probe_Z_summary():
    print("\n" + "=" * 72)
    for n, o, d in RESULTS:
        print(f"{o:34} {n}")
    print("=" * 72)
