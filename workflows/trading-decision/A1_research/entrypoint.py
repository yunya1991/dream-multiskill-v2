import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def run_a1_research(payload: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Thin wrapper for A1 research artifact output."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = Path(output_dir) if output_dir is not None else Path("artifacts/trading")
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / f"a1_research_{ts}.json"

    result = {
        "stage_id": "A1",
        "trace_id": payload.get("trace_id"),
        "signals": list(payload.get("signals") or []),
        "confidence": float(payload.get("confidence") or 0.0),
        "timestamp": ts,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["artifact_path"] = str(out_path)
    return result
