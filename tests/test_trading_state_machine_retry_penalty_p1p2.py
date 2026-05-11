import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path("/Users/zhangjiangtao/WorkBuddy/dream-multiskill-v2")


def _load_module(rel_path: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_state_machine_rejects_invalid_transition():
    mod = _load_module("workflows/trading-decision/orchestrator/state_machine.py")
    sm = mod.TradingStateMachine()
    with pytest.raises(ValueError):
        sm.transition("EXECUTION")


def test_retry_and_penalty_accumulates_then_succeeds():
    mod = _load_module("workflows/trading-decision/orchestrator/state_machine.py")
    ledger = mod.ReputationLedger()
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("EVIDENCE_INCOMPLETE")
        return {"ok": True}

    out = mod.execute_with_retry(flaky, max_retries=3, ledger=ledger, module_name="A4")
    assert out["result"]["ok"] is True
    assert out["attempts"] == 3
    assert ledger.score("A4") < 100


def test_retry_returns_degraded_when_exhausted():
    mod = _load_module("workflows/trading-decision/orchestrator/state_machine.py")
    ledger = mod.ReputationLedger()

    def always_fail():
        raise RuntimeError("CONSTRAINT_VALIDATION_FAILED")

    out = mod.execute_with_retry(always_fail, max_retries=1, ledger=ledger, module_name="A2")
    assert out["status"] == "DEGRADED"
    assert out["error_code"] == "CONSTRAINT_VALIDATION_FAILED"


def test_governance_feedback_penalizes_and_recovers_score():
    mod = _load_module("workflows/trading-decision/orchestrator/state_machine.py")
    ledger = mod.ReputationLedger()
    mod.apply_governance_feedback(
        ledger=ledger,
        a7_output={"audit_status": "REVIEW", "violations": [{"id": "v1"}]},
        a8_output={"gap_score": 0.35},
    )
    assert ledger.score("A7") < 100
    assert ledger.score("A8") < 100

    mod.apply_governance_feedback(
        ledger=ledger,
        a7_output={"audit_status": "PASS", "violations": []},
        a8_output={"gap_score": 0.02},
    )
    assert ledger.score("A7") >= 90
