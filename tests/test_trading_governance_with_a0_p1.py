import importlib.util
from pathlib import Path


REPO_ROOT = Path("/Users/zhangjiangtao/WorkBuddy/dream-multiskill-v2")


def _load_module(rel_path: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 1. Governance loop A0→A7→A8→A2 full chain
# ---------------------------------------------------------------------------

def test_governance_loop_runs_a0_then_a9_a7_a8_a2(tmp_path: Path):
    """Per spec: governance loop starts with A0(矛盾监控) before A7/A8."""
    mod = _load_module("workflows/trading-decision/orchestrator/governance_loop.py")
    out = mod.run_governance_loop(
        {
            "trace_id": "trace-gov-a0",
            "contradictions": [
                {"id": "cx_macro", "score": 2.5, "direction": "DOWN"},
            ],
            "unrealized_pnl_pct": 1.2,
            "risk_level": "medium",
            "violations": [],
            "hypothesis_score": 0.74,
            "practice_score": 0.71,
        },
        output_dir=tmp_path,
        now_ts="2026-05-11T14:00:00+00:00",
    )
    # A0 must be the first visited stage
    assert out["visited_stages"][0] == "A0"
    assert "A0" in out["stage_outputs"]
    # A0 output should contain the primary contradiction
    a0_payload = out["stage_outputs"]["A0"]
    assert a0_payload.get("primary_contradiction", {}).get("id") == "cx_macro"


# ---------------------------------------------------------------------------
# 2. Knowledge-synthesis routing: gap ≤ 0.1 → A2, gap > 0.1 → A3
# ---------------------------------------------------------------------------

def test_gap_score_005_routes_to_a2(tmp_path: Path):
    """gap_score ≤ 0.1 should route to A2 (first principles update)."""
    mod = _load_module("workflows/trading-decision/orchestrator/governance_loop.py")
    out = mod.run_governance_loop(
        {
            "trace_id": "trace-gap-a2",
            "unrealized_pnl_pct": 0.5,
            "risk_level": "low",
            "violations": [],
            "hypothesis_score": 0.72,
            "practice_score": 0.70,  # gap = 0.02
        },
        output_dir=tmp_path,
        now_ts="2026-05-11T14:00:00+00:00",
    )
    assert "A2" in out["visited_stages"]


def test_gap_score_025_routes_to_a3(tmp_path: Path):
    """gap_score > 0.1 should route to A3 (simulation update)."""
    mod = _load_module("workflows/trading-decision/orchestrator/governance_loop.py")
    out = mod.run_governance_loop(
        {
            "trace_id": "trace-gap-a3",
            "unrealized_pnl_pct": 0.5,
            "risk_level": "low",
            "violations": [],
            "hypothesis_score": 0.80,
            "practice_score": 0.55,  # gap = 0.25
        },
        output_dir=tmp_path,
        now_ts="2026-05-11T14:00:00+00:00",
    )
    assert "A3" in out["visited_stages"]


# ---------------------------------------------------------------------------
# 3. ReputationLedger cumulative penalty
# ---------------------------------------------------------------------------

def test_reputation_cumulative_penalty(tmp_path: Path):
    """Consecutive failures should continuously decrease reputation score."""
    state_mod = _load_module("workflows/trading-decision/orchestrator/state_machine.py")
    ledger = state_mod.ReputationLedger()

    # First failure: A7 REVIEW + gap 0.35
    state_mod.apply_governance_feedback(
        ledger=ledger,
        a7_output={"audit_status": "REVIEW", "violations": [{"id": "v1"}]},
        a8_output={"gap_score": 0.35},
    )
    score_after_1 = ledger.score("A7")

    # Second failure: A7 REVIEW + gap 0.50
    state_mod.apply_governance_feedback(
        ledger=ledger,
        a7_output={"audit_status": "REVIEW", "violations": [{"id": "v2"}]},
        a8_output={"gap_score": 0.50},
    )
    score_after_2 = ledger.score("A7")

    assert score_after_2 < score_after_1


def test_reputation_recovery_after_success(tmp_path: Path):
    """Successful governance should recover reputation score."""
    state_mod = _load_module("workflows/trading-decision/orchestrator/state_machine.py")
    ledger = state_mod.ReputationLedger()

    # Fail first
    state_mod.apply_governance_feedback(
        ledger=ledger,
        a7_output={"audit_status": "REVIEW", "violations": [{"id": "v1"}]},
        a8_output={"gap_score": 0.40},
    )
    score_low = ledger.score("A7")
    assert score_low < 100

    # Then succeed
    state_mod.apply_governance_feedback(
        ledger=ledger,
        a7_output={"audit_status": "PASS", "violations": []},
        a8_output={"gap_score": 0.02},
    )
    score_high = ledger.score("A7")
    assert score_high > score_low


# ---------------------------------------------------------------------------
# 4. Daily 14:00 trigger vs event trigger
# ---------------------------------------------------------------------------

def test_governance_a8_triggered_by_daily_schedule(tmp_path: Path):
    """A8 should run at exactly 14:00 UTC."""
    mod = _load_module("workflows/trading-decision/orchestrator/governance_loop.py")
    out = mod.run_governance_loop(
        {
            "trace_id": "trace-daily",
            "unrealized_pnl_pct": 0.3,
            "risk_level": "low",
            "violations": [],
            "hypothesis_score": 0.80,
            "practice_score": 0.78,
        },
        output_dir=tmp_path,
        now_ts="2026-05-11T14:00:00+00:00",
    )
    assert "A8" in out["visited_stages"]


def test_governance_a8_triggered_by_event_off_schedule(tmp_path: Path):
    """Event trigger should run A8 even when not 14:00."""
    mod = _load_module("workflows/trading-decision/orchestrator/governance_loop.py")
    out = mod.run_governance_loop(
        {
            "trace_id": "trace-event",
            "trigger_source": "event",
            "unrealized_pnl_pct": 0.3,
            "risk_level": "low",
            "violations": [],
            "hypothesis_score": 0.80,
            "practice_score": 0.78,
        },
        output_dir=tmp_path,
        now_ts="2026-05-11T09:00:00+00:00",  # not 14:00
    )
    assert "A8" in out["visited_stages"]


def test_governance_a8_runs_by_default_after_a7(tmp_path: Path):
    """Default event trigger always runs A8 after A7 (知行合一 check)."""
    mod = _load_module("workflows/trading-decision/orchestrator/governance_loop.py")
    out = mod.run_governance_loop(
        {
            "trace_id": "trace-default-a8",
            "unrealized_pnl_pct": 0.3,
            "risk_level": "low",
            "violations": [],
        },
        output_dir=tmp_path,
        now_ts="2026-05-11T09:00:00+00:00",  # not 14:00
    )
    # Default trigger_source is "event" → A8 runs
    assert "A8" in out["visited_stages"]
    assert "reputation" in out
