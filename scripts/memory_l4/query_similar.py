import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.memory_l4.paths import workbuddy_dir


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def _bool_match(a: Any, b: Any) -> float:
    if a is None or b is None:
        return 0.0
    return 1.0 if a == b else 0.0


def _norm_edge(edge: Any) -> float:
    if edge is None:
        return 0.5
    x = float(edge)
    x = max(-200.0, min(200.0, x))
    return (x + 200.0) / 400.0


def _norm_score(v: Any) -> float:
    if v is None:
        return 0.0
    x = float(v)
    x = max(0.0, min(100.0, x))
    return x / 100.0


def _cosine(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot / (n1 * n2)


def _strategy_score(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    if a.get("matched_strategy") and a.get("matched_strategy") == b.get("matched_strategy"):
        return 1.0
    if a.get("category") and a.get("category") == b.get("category"):
        return 0.6
    return 0.0


def _collect_distill_refs(index_data: Dict[str, Any], case_id: str, limit: int = 3) -> Dict[str, List[str]]:
    distills = index_data.get("distill_features") or {}
    claims: List[str] = []
    rules: List[str] = []
    for d in distills.values():
        if case_id not in (d.get("supporting_case_ids") or []):
            continue
        c = str(d.get("claim") or "").strip()
        if c:
            claims.append(c)
        for r in (d.get("actionable_rules") or []):
            rs = str(r).strip()
            if rs:
                rules.append(rs)
    return {"claim": claims[:limit], "actionable_rules": rules[:limit]}


def _case_lessons(f: Dict[str, Any], limit: int = 3) -> List[str]:
    refs = f.get("references") or {}
    lessons = refs.get("case_lessons") or []
    out = [str(x) for x in lessons if str(x)]
    return out[:limit]


def _explain(a: Dict[str, Any], b: Dict[str, Any], score_keys: List[str]) -> Dict[str, Any]:
    overlap = list(set(a.get("reason_codes") or []) & set(b.get("reason_codes") or []))
    overlap.sort()

    num_hits: Dict[str, Any] = {}
    a_edge = a.get("edge")
    b_edge = b.get("edge")
    if a_edge is not None and b_edge is not None:
        num_hits["edge_diff"] = float(a_edge) - float(b_edge)
    a_ts = a.get("total_score")
    b_ts = b.get("total_score")
    if a_ts is not None and b_ts is not None:
        num_hits["total_score_diff"] = float(a_ts) - float(b_ts)

    for k in score_keys:
        if k in ("edge", "total_score"):
            continue
        av = (a.get("scores") or {}).get(k)
        bv = (b.get("scores") or {}).get(k)
        if av is None or bv is None:
            continue
        num_hits[f"{k}_diff"] = float(av) - float(bv)

    return {
        "struct_hits": {
            "regime_match": _bool_match(a.get("regime"), b.get("regime")),
            "decision_match": _bool_match(a.get("decision"), b.get("decision")),
            "reason_overlap": overlap
        },
        "num_hits": num_hits,
        "strategy_hits": {
            "matched_strategy": a.get("matched_strategy") if a.get("matched_strategy") == b.get("matched_strategy") else None,
            "category_match": _bool_match(a.get("category"), b.get("category"))
        }
    }


def _numeric_common_keys(a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
    a_scores = a.get("scores") or {}
    b_scores = b.get("scores") or {}
    common = sorted([k for k in a_scores.keys() if k in b_scores])
    common.extend(["total_score", "edge"])
    return common


def similarity(index_data: Dict[str, Any], a_id: str, b_id: str) -> Tuple[float, Dict[str, Any]]:
    feats = index_data.get("case_features") or {}
    a = feats.get(a_id) or {}
    b = feats.get(b_id) or {}
    weights = (index_data.get("metadata") or {}).get("weights") or {"struct": 0.4, "num": 0.4, "strategy": 0.2}

    sim_struct = 0.0
    sim_struct += 0.4 * _bool_match(a.get("regime"), b.get("regime"))
    sim_struct += 0.2 * _bool_match(a.get("decision"), b.get("decision"))
    sim_struct += 0.3 * _jaccard(a.get("reason_codes") or [], b.get("reason_codes") or [])
    sim_struct += 0.1 * _jaccard(a.get("tags") or [], b.get("tags") or [])

    common = _numeric_common_keys(a, b)
    va: List[float] = []
    vb: List[float] = []
    for k in common:
        if k == "edge":
            va.append(_norm_edge(a.get("edge")))
            vb.append(_norm_edge(b.get("edge")))
        elif k == "total_score":
            va.append(_norm_score(a.get("total_score")))
            vb.append(_norm_score(b.get("total_score")))
        else:
            va.append(_norm_score((a.get("scores") or {}).get(k)))
            vb.append(_norm_score((b.get("scores") or {}).get(k)))

    sim_num = _cosine(va, vb)
    sim_strategy = _strategy_score(a, b)

    sim = float(weights.get("struct", 0.4)) * sim_struct + float(weights.get("num", 0.4)) * sim_num + float(weights.get("strategy", 0.2)) * sim_strategy
    return sim, _explain(a, b, score_keys=common)


def query_similar_cases(index_data: Dict[str, Any], case_id: str, topk: int = 10) -> Dict[str, Any]:
    feats = index_data.get("case_features") or {}
    if case_id not in feats:
        raise KeyError(f"case_id not found: {case_id}")

    scored: List[Tuple[str, float, Dict[str, Any]]] = []
    for other_id in feats.keys():
        if other_id == case_id:
            continue
        s, expl = similarity(index_data, case_id, other_id)
        scored.append((other_id, s, expl))

    scored.sort(key=lambda x: (-x[1], x[0]))
    top = scored[: max(0, int(topk))]

    results: List[Dict[str, Any]] = []
    for rank, (oid, s, expl) in enumerate(top, start=1):
        f = feats.get(oid) or {}
        results.append(
            {
                "rank": rank,
                "case_id": oid,
                "similarity": s,
                "explain": expl,
                "references": {
                    "case_lessons": _case_lessons(f, limit=3),
                    "distill_refs": _collect_distill_refs(index_data, oid, limit=3)
                }
            }
        )

    return {
        "query": {
            "case_id": case_id,
            "weights": (index_data.get("metadata") or {}).get("weights")
        },
        "results": results
    }


def default_index_path() -> Path:
    return workbuddy_dir() / "memory_l4" / "index" / "latest.json"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--topk", required=False, default="10")
    parser.add_argument("--index", required=False)
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    index_path = Path(args.index) if args.index else default_index_path()
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    out = query_similar_cases(index_data, case_id=args.case, topk=int(args.topk))

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(out_path))
        return

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

