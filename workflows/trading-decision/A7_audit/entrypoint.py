import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def run_a7_audit(payload: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Thin wrapper for A7 audit output."""
    violations: List[Dict[str, Any]] = list(payload.get('violations') or [])
    status = 'PASS' if not violations else 'REVIEW'

    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base = Path(output_dir) if output_dir is not None else Path('artifacts/trading')
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / f'a7_audit_{ts}.json'

    result = {
        'stage_id': 'A7',
        'trace_id': payload.get('trace_id'),
        'checks': payload.get('checks') or {},
        'violations': violations,
        'audit_status': status,
        'timestamp': ts,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result['artifact_path'] = str(out_path)
    return result
