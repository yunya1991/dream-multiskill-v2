import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.memory_l4.paths import memory_l4_cases_dir, memory_l4_distills_dir, workbuddy_dir


DEFAULT_WEIGHTS = {"struct": 0.4, "num": 0.4, "strategy": 0.2}


def now_iso_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_json_files(dir_path: Path) -> List[Path]:
    if not dir_path.exists():
        return []
    return sorted([p for p in dir_path.glob("*.json") if p.is_file()])


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


def _safe_get(d: Dict[str, Any], keys: List[str]) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _extract_episode_ref_path(case: Dict[str, Any]) -> Optional[str]:
    ex = case.get("execution") or {}
    refs = ex.get("episode_refs") or []
    if not refs:
        return None
    p = refs[0].get("path")
    return str(p) if p else None


def _read_episode_by_ref(episode_ref_path: Optional[str]) -> Dict[str, Any]:
    if not episode_ref_path:
        return {}
    p = Path(episode_ref_path)
    if not p.is_absolute():
        p = _ROOT / p
    if not p.exists():
        return {}
    try:
        return load_json(p)
    except Exception:
        return {}


def _case_review_lessons(case: Dict[str, Any], limit: int = 3) -> List[str]:
    review = case.get("review") or {}
    lessons = review.get("lessons") or []
    out = [str(x) for x in lessons if str(x)]
    if out:
        return out[:limit]
    summary = str(review.get("summary") or "").strip()
    if not summary:
        return []
    parts = [p.strip() for p in summary.replace("。", ".").split(".") if p.strip()]
    return parts[:limit]


def build_index_data(
    snapshot_ts: str,
    cases: List[Dict[str, Any]],
    distills: List[Dict[str, Any]],
    episodes_by_path: Dict[str, Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    w = weights or DEFAULT_WEIGHTS

    case_features: Dict[str, Any] = {}
    for c in cases:
        cid = str(c.get("case_id") or "")
        if not cid:
            continue

        env = c.get("environment_snapshot") or {}
        regime = env.get("regime")

        episode_path = _extract_episode_ref_path(c)
        ep = episodes_by_path.get(episode_path or "", {})

        decision = ep.get("decision")
        reason_codes = ep.get("reason_codes") or []
        edge = ep.get("edge")
        total_score = ep.get("total_score")
        scores = ep.get("scores") or {}

        directive = _safe_get(ep, ["strategy_result", "strategy_directive"]) or {}
        matched_strategy = directive.get("matched_strategy")
        category = directive.get("category")
        directive_bias = directive.get("directive_bias")

        case_features[cid] = {
            "inst_id": c.get("inst_id"),
            "regime": regime,
            "decision": decision,
            "reason_codes": [str(x) for x in reason_codes if str(x)],
            "tags": [str(x) for x in (c.get("tags") or []) if str(x)],
            "scores": scores,
            "total_score": total_score,
            "edge": edge,
            "matched_strategy": matched_strategy,
            "category": category,
            "directive_bias": directive_bias,
            "references": {"case_lessons": _case_review_lessons(c, limit=3)}
        }

    distill_features: Dict[str, Any] = {}
    for d in distills:
        did = str(d.get("distill_id") or "")
        if not did:
            continue
        distill_features[did] = {
            "kind": d.get("kind"),
            "claim": str(d.get("claim") or "").strip(),
            "actionable_rules": [str(x) for x in (d.get("actionable_rules") or []) if str(x)],
            "supporting_case_ids": [str(x) for x in (d.get("supporting_case_ids") or []) if str(x)]
        }

    return {
        "metadata": {
            "snapshot_ts": snapshot_ts,
            "feature_version": "v0.1",
            "weights": {"struct": float(w["struct"]), "num": float(w["num"]), "strategy": float(w["strategy"])}
        },
        "case_features": case_features,
        "distill_features": distill_features
    }


def load_episodes_for_cases(cases: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for c in cases:
        p = _extract_episode_ref_path(c)
        if not p:
            continue
        out[str(p)] = _read_episode_by_ref(p)
    return out


def default_index_path() -> Path:
    return workbuddy_dir() / "memory_l4" / "index" / "latest.json"


def write_index(index_data: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    cases = load_cases()
    distills = load_distills()
    episodes = load_episodes_for_cases(cases)
    data = build_index_data(now_iso_local(), cases, distills, episodes_by_path=episodes)

    out_path = Path(args.out) if args.out else default_index_path()
    written = write_index(data, out_path)
    print(str(written))


if __name__ == "__main__":
    main()

