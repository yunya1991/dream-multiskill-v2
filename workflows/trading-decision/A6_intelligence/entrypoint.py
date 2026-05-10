import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def run_a6_intelligence(payload: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Thin wrapper for A6 intelligence summary output."""
    alerts: List[Dict[str, Any]] = list(payload.get('alerts') or [])
    signal_shift = float(payload.get('signal_shift') or 0.0)

    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base = Path(output_dir) if output_dir is not None else Path('artifacts/trading')
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / f'a6_intelligence_{ts}.json'

    result = {
        'stage_id': 'A6',
        'trace_id': payload.get('trace_id'),
        'alert_count': len(alerts),
        'alerts': alerts,
        'signal_shift': signal_shift,
        'timestamp': ts,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result['artifact_path'] = str(out_path)
    return result
