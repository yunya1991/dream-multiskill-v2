from pathlib import Path


def test_build_stats_snapshot(tmp_path: Path):
    from scripts.memory_l4.stats_builder import build_stats_snapshot

    cases = [
        {
            "case_id": "TC_1",
            "ts_start": "2026-01-01T00:00:00+08:00",
            "inst_id": "BTC-USDT-SWAP",
            "tags": ["t1"],
            "environment_snapshot": {"regime": "RANGE_BOUND"},
            "quadrant": {
                "x": 0.5,
                "y": 0.6,
                "evidence": {
                    "weights": {"perf": 0.4, "consistency": 0.4, "human": 0.2},
                    "y_perf": 0.6,
                    "y_consistency": 0.6,
                    "y_human": 0.6
                }
            }
        }
    ]
    distills = [
        {
            "distill_id": "D_1",
            "kind": "risk_signal",
            "claim": "test",
            "supporting_case_ids": ["TC_1"],
            "quadrant": {
                "x": -0.5,
                "y": 0.7,
                "evidence": {
                    "weights": {"perf": 0.4, "consistency": 0.4, "human": 0.2},
                    "y_perf": 0.7,
                    "y_consistency": 0.7,
                    "y_human": 0.7
                }
            },
            "migration_history": [
                {"ts": "2026-01-01T00:00:00+08:00", "y_prev": 0.2, "y_new": 0.7, "reason": "new_case", "note": ""}
            ]
        }
    ]

    stats = build_stats_snapshot(snapshot_ts="2026-01-01T00:00:00+08:00", cases=cases, distills=distills)

    assert stats["snapshot_ts"] == "2026-01-01T00:00:00+08:00"
    assert len(stats["points"]) == 2
    assert len(stats["migration_trends"]) == 1
    assert stats["migration_trends"][0]["id"] == "D_1"


def test_build_stats_snapshot_performance_metrics():
    from scripts.memory_l4.stats_builder import build_stats_snapshot

    cases = [
        {"case_id": "TC_1", "ts_start": "2026-01-01T00:00:00+08:00", "environment_snapshot": {}, "quadrant": {}},
        {"case_id": "TC_2", "ts_start": "2026-01-02T00:00:00+08:00", "environment_snapshot": {}, "quadrant": {}},
        {"case_id": "TC_3", "ts_start": "2026-01-03T00:00:00+08:00", "environment_snapshot": {}, "quadrant": {}},
    ]
    episodes_by_case_id = {
        "TC_1": {"outcome": {"unrealized_pnl_usdt": 10.0, "unrealized_pnl_pct": 1.0}},
        "TC_2": {"outcome": {"unrealized_pnl_usdt": -5.0, "unrealized_pnl_pct": -0.5}},
        "TC_3": {"outcome": {"unrealized_pnl_usdt": 5.0, "unrealized_pnl_pct": 0.4}},
    }

    stats = build_stats_snapshot(
        snapshot_ts="2026-01-03T00:00:00+08:00",
        cases=cases,
        distills=[],
        episodes_by_case_id=episodes_by_case_id,
    )

    perf = stats["performance"]
    assert perf["n_cases"] == 3
    assert perf["n_with_outcome"] == 3
    assert perf["wins"] == 2
    assert perf["losses"] == 1
    assert perf["win_rate"] == 0.6667
    assert perf["avg_pnl_usdt"] == 3.3333
    assert perf["avg_pnl_pct"] == 0.3
    assert perf["profit_factor"] == 3.0
    assert perf["max_drawdown"] == 5.0
