import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.memory_l4.paths import memory_l4_cases_dir, memory_l4_distills_dir, memory_l4_stats_dir


def now_iso_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_json_files(dir_path: Path) -> List[Path]:
    if not dir_path.exists():
        return []
    return sorted([p for p in dir_path.glob("*.json") if p.is_file()])


def build_point_from_case(case: Dict[str, Any]) -> Dict[str, Any]:
    q = case.get("quadrant") or {}
    env = case.get("environment_snapshot") or {}
    return {
        "id": str(case.get("case_id") or ""),
        "kind": "case",
        "x": float(q.get("x") or 0.0),
        "y": float(q.get("y") or 0.0),
        "inst_id": case.get("inst_id"),
        "regime": env.get("regime"),
        "tags": case.get("tags") or []
    }


def build_point_from_distill(distill: Dict[str, Any]) -> Dict[str, Any]:
    q = distill.get("quadrant") or {}
    return {
        "id": str(distill.get("distill_id") or ""),
        "kind": "distill",
        "x": float(q.get("x") or 0.0),
        "y": float(q.get("y") or 0.0),
        "inst_id": None,
        "regime": None,
        "tags": []
    }


def build_migration_trends(snapshot_ts: str, distills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for d in distills:
        did = str(d.get("distill_id") or "")
        if not did:
            continue
        q = d.get("quadrant") or {}
        y_now = float(q.get("y") or 0.0)
        history = d.get("migration_history") or []

        series: List[Dict[str, Any]] = []
        for rec in history:
            ts = rec.get("ts")
            y_new = rec.get("y_new")
            if ts is None or y_new is None:
                continue
            series.append({"ts": str(ts), "y": float(y_new)})
        series.append({"ts": snapshot_ts, "y": y_now})

        out.append({"id": did, "kind": "distill", "series": series})
    return out


def _count_by(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for it in items:
        v = it.get(key)
        if not v:
            continue
        out[str(v)] = out.get(str(v), 0) + 1
    return out


def _episode_pnl(ep: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    out = ep.get("outcome") or {}
    pos = ep.get("position") or {}
    pnl_usdt = out.get("unrealized_pnl_usdt")
    if pnl_usdt is None:
        pnl_usdt = out.get("unrealized_pnl")
    if pnl_usdt is None:
        pnl_usdt = pos.get("upl")
    pnl_pct = out.get("unrealized_pnl_pct")
    return (
        float(pnl_usdt) if pnl_usdt is not None else None,
        float(pnl_pct) if pnl_pct is not None else None,
    )


def _extract_episode_ref_path(case: Dict[str, Any]) -> Optional[str]:
    refs = ((case.get("execution") or {}).get("episode_refs") or [])
    if not refs:
        return None
    p = str((refs[0] or {}).get("path") or "").strip()
    return p if p else None


def _read_episode(path: str) -> Dict[str, Any]:
    ep = Path(path)
    if not ep.is_absolute():
        ep = _ROOT / ep
    if not ep.exists():
        return {}
    try:
        return load_json(ep)
    except Exception:
        return {}


def _load_episodes_by_case_id(cases: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for c in cases:
        cid = str(c.get("case_id") or "")
        if not cid:
            continue
        p = _extract_episode_ref_path(c)
        out[cid] = _read_episode(p) if p else {}
    return out


def _compute_max_drawdown(series: List[float]) -> float:
    if not series:
        return 0.0
    peak = series[0]
    mdd = 0.0
    for v in series:
        if v > peak:
            peak = v
        drawdown = peak - v
        if drawdown > mdd:
            mdd = drawdown
    return mdd


def build_performance(cases: List[Dict[str, Any]], episodes_by_case_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    wins = 0
    losses = 0
    n_with_outcome = 0
    pnl_usdts: List[float] = []
    pnl_pcts: List[float] = []

    # Use case time order to build cumulative PnL drawdown.
    ordered_cases = sorted(cases, key=lambda c: str(c.get("ts_start") or ""))
    cum = 0.0
    equity_curve: List[float] = [0.0]
    for c in ordered_cases:
        cid = str(c.get("case_id") or "")
        ep = episodes_by_case_id.get(cid) or {}
        pnl_usdt, pnl_pct = _episode_pnl(ep)
        if pnl_usdt is None and pnl_pct is None:
            continue
        n_with_outcome += 1
        if pnl_pct is not None:
            pnl_pcts.append(float(pnl_pct))
            if pnl_pct > 0:
                wins += 1
            elif pnl_pct < 0:
                losses += 1
        elif pnl_usdt is not None:
            if pnl_usdt > 0:
                wins += 1
            elif pnl_usdt < 0:
                losses += 1
        if pnl_usdt is not None:
            pnl_usdts.append(float(pnl_usdt))
            cum += float(pnl_usdt)
            equity_curve.append(cum)

    denom = wins + losses
    win_rate = (float(wins) / float(denom)) if denom > 0 else 0.0
    avg_pnl_usdt = (sum(pnl_usdts) / len(pnl_usdts)) if pnl_usdts else None
    avg_pnl_pct = (sum(pnl_pcts) / len(pnl_pcts)) if pnl_pcts else None
    gross_win = sum(x for x in pnl_usdts if x > 0)
    gross_loss = abs(sum(x for x in pnl_usdts if x < 0))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else None
    mdd = _compute_max_drawdown(equity_curve) if pnl_usdts else None

    return {
        "n_cases": len(cases),
        "n_with_outcome": n_with_outcome,
        "wins": wins,
        "losses": losses,
        "win_rate": round(float(win_rate), 4),
        "avg_pnl_usdt": round(float(avg_pnl_usdt), 4) if avg_pnl_usdt is not None else None,
        "avg_pnl_pct": round(float(avg_pnl_pct), 4) if avg_pnl_pct is not None else None,
        "profit_factor": round(float(profit_factor), 4) if profit_factor is not None else None,
        "max_drawdown": round(float(mdd), 4) if mdd is not None else None,
    }


def build_stats_snapshot(
    snapshot_ts: str,
    cases: List[Dict[str, Any]],
    distills: List[Dict[str, Any]],
    episodes_by_case_id: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    points: List[Dict[str, Any]] = []
    for c in cases:
        points.append(build_point_from_case(c))
    for d in distills:
        points.append(build_point_from_distill(d))

    aggregations: Dict[str, Any] = {
        "cases_by_inst_id": _count_by(cases, "inst_id"),
        "cases_by_regime": _count_by([c.get("environment_snapshot") or {} for c in cases], "regime"),
        "distills_by_kind": _count_by(distills, "kind")
    }
    episodes = episodes_by_case_id if episodes_by_case_id is not None else _load_episodes_by_case_id(cases)

    return {
        "version": "v0.1",
        "snapshot_ts": snapshot_ts,
        "points": points,
        "performance": build_performance(cases, episodes),
        "aggregations": aggregations,
        "migration_trends": build_migration_trends(snapshot_ts, distills)
    }


def write_stats_latest(stats: Dict[str, Any]) -> Path:
    out_dir = memory_l4_stats_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest.json"
    out_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def load_cases() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in list_json_files(memory_l4_cases_dir()):
        out.append(load_json(p))
    return out


def load_distills() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in list_json_files(memory_l4_distills_dir()):
        out.append(load_json(p))
    return out


def main() -> None:
    stats = build_stats_snapshot(now_iso_local(), load_cases(), load_distills())
    out_path = write_stats_latest(stats)
    print(str(out_path))


if __name__ == "__main__":
    main()
