"""统计引擎模块 — 象限驱动的全局统计。

从全部 TradeCase / ReviewRecord / DistillRecord 中聚合：
- 象限分布、A0-A9 阶段覆盖率、胜率、平均收益
- L4 状态机分布、错误码分布

v0.2 新增模块 — Phase P0
"""

import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.memory_l4.paths import (
    memory_l4_cases_dir,
    memory_l4_distills_dir,
    memory_l4_reviews_dir,
    memory_l4_stats_dir,
)


def now_iso_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _list_json(dir_path: Path) -> List[Path]:
    if not dir_path.exists():
        return []
    return sorted([p for p in dir_path.glob("*.json") if p.is_file()])


def _load_all_cases() -> List[Dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in _list_json(memory_l4_cases_dir())]


def compute_stage_coverage(cases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """统计 A0-A9 各阶段覆盖情况。"""
    if cases is None:
        cases = _load_all_cases()
    stage_counts = {f"A{i}": 0 for i in range(10)}
    total = len(cases)
    for c in cases:
        seen = set()
        for entry in c.get("thinking_chain") or []:
            s = entry.get("stage")
            if s and s in stage_counts:
                seen.add(s)
        for s in seen:
            stage_counts[s] += 1
    return {
        "total_cases": total,
        "stage_counts": stage_counts,
        "stage_rates": {s: round(v / total, 3) if total else 0 for s, v in stage_counts.items()},
    }


def compute_quadrant_distribution(cases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """统计象限分布。"""
    if cases is None:
        cases = _load_all_cases()
    xs, ys = [], []
    for c in cases:
        q = c.get("quadrant") or {}
        if q.get("x") is not None and q.get("y") is not None:
            xs.append(q["x"])
            ys.append(q["y"])
    return {
        "count": len(xs),
        "x_mean": round(sum(xs) / len(xs), 3) if xs else 0,
        "y_mean": round(sum(ys) / len(ys), 3) if ys else 0,
        "x_range": [round(min(xs), 3), round(max(xs), 3)] if xs else [0, 0],
        "y_range": [round(min(ys), 3), round(max(ys), 3)] if ys else [0, 0],
    }


def compute_pnl_stats(cases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """统计收益分布。"""
    if cases is None:
        cases = _load_all_cases()
    pnls = []
    for c in cases:
        do = c.get("decision_outcome") or {}
        p = do.get("pnl_pct")
        if p is not None:
            pnls.append(float(p))
    if not pnls:
        return {"count": 0, "mean": 0, "median": 0, "win_rate": 0, "max": 0, "min": 0}
    pnls.sort()
    wins = sum(1 for p in pnls if p > 0)
    return {
        "count": len(pnls),
        "mean": round(sum(pnls) / len(pnls), 3),
        "median": round(pnls[len(pnls) // 2], 3),
        "win_rate": round(wins / len(pnls), 3),
        "max": round(max(pnls), 3),
        "min": round(min(pnls), 3),
    }


def compute_l4_status_distribution(cases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """统计 L4 状态机分布。"""
    if cases is None:
        cases = _load_all_cases()
    status_counts: Dict[str, int] = {}
    for c in cases:
        s = c.get("l4_status") or "UNKNOWN"
        status_counts[s] = status_counts.get(s, 0) + 1
    total = len(cases)
    return {
        "total": total,
        "distribution": status_counts,
        "rates": {s: round(v / total, 3) if total else 0 for s, v in status_counts.items()},
    }


def compute_full_stats(snapshot_ts: Optional[str] = None) -> Dict[str, Any]:
    """聚合全部统计，产出 StatsSnapshot。"""
    ts = snapshot_ts or now_iso_local()
    cases = _load_all_cases()
    return {
        "snapshot_id": f"STATS_{ts.replace(':', '').replace('-', '').replace('+', '')[:15]}",
        "snapshot_ts": ts,
        "version": "v0.2",
        "stage_coverage": compute_stage_coverage(cases),
        "quadrant_distribution": compute_quadrant_distribution(cases),
        "pnl_stats": compute_pnl_stats(cases),
        "l4_status_distribution": compute_l4_status_distribution(cases),
        "distill_count": len(_list_json(memory_l4_distills_dir())),
        "review_count": len(_list_json(memory_l4_reviews_dir())),
    }


def save_stats(stats: Dict[str, Any], out_path: Optional[Path] = None) -> Path:
    """保存统计快照。"""
    target = out_path or (memory_l4_stats_dir() / f"{stats['snapshot_id']}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
