import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(rel_path: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_governance_loop_runs_a9_a7_a8_and_routes_to_a2(tmp_path: Path):
    mod = _load_module("workflows/trading-decision/orchestrator/governance_loop.py")

    out = mod.run_governance_loop(
        {
            "trace_id": "trace-gov-1",
            "unrealized_pnl_pct": 1.2,
            "risk_level": "medium",
            "violations": [],
            "hypothesis_score": 0.74,
            "practice_score": 0.71,
        },
        output_dir=tmp_path,
        now_ts="2026-05-11T14:00:00+00:00",
    )

    assert out["trace_id"] == "trace-gov-1"
    assert out["visited_stages"][:3] == ["A9", "A7", "A8"]
    assert out["visited_stages"][-1] == "A2"
    assert {"A9", "A7", "A8", "A2"}.issubset(set(out["stage_outputs"].keys()))
    assert any(m["header"]["loop_type"] == "governance" for m in out["messages"])


def test_a8_daily_trigger_only_runs_at_1400_utc():
    mod = _load_module("workflows/trading-decision/orchestrator/governance_loop.py")
    assert mod.should_trigger_a8("2026-05-11T14:00:00+00:00")
    assert not mod.should_trigger_a8("2026-05-11T13:59:00+00:00")


def test_governance_event_trigger_runs_a8_even_when_not_1400(tmp_path: Path):
    mod = _load_module("workflows/trading-decision/orchestrator/governance_loop.py")
    out = mod.run_governance_loop(
        {
            "trace_id": "trace-gov-2",
            "unrealized_pnl_pct": 0.5,
            "risk_level": "low",
            "violations": [],
            "hypothesis_score": 0.88,
            "practice_score": 0.80,
        },
        output_dir=tmp_path,
        now_ts="2026-05-11T13:00:00+00:00",
    )
    assert "A8" in out["visited_stages"]
    assert "A2" in out["visited_stages"] or "A3" in out["visited_stages"]
    assert "reputation" in out
