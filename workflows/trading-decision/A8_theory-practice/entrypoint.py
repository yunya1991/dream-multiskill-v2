import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def run_a8_theory_practice(payload: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Thin wrapper for A8 theory-practice verification output."""
    hypo = float(payload.get('hypothesis_score') or 0.0)
    prac = float(payload.get('practice_score') or 0.0)
    gap = abs(hypo - prac)

    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base = Path(output_dir) if output_dir is not None else Path('artifacts/trading')
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / f'a8_theory_practice_{ts}.json'

    result = {
        'stage_id': 'A8',
        'trace_id': payload.get('trace_id'),
        'hypothesis_score': hypo,
        'practice_score': prac,
        'gap_score': gap,
        'timestamp': ts,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result['artifact_path'] = str(out_path)
    return result
