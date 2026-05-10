from typing import Any, Dict, List


def run_a0_contradiction_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Thin wrapper for A0 contradiction ranking."""
    items: List[Dict[str, Any]] = list(payload.get("contradictions") or [])
    items.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    primary = items[0] if items else {"id": "none", "score": 0.0, "direction": "NEUTRAL"}
    direction = str(primary.get("direction") or "NEUTRAL")
    return {
        "stage_id": "A0",
        "trace_id": payload.get("trace_id"),
        "primary_contradiction": primary,
        "direction": direction,
        "total_contradictions": len(items),
    }
