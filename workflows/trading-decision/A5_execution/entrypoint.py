import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def run_a5_execution(payload: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Thin wrapper for A5 execution plan artifact output."""
    direction = str(payload.get('direction') or 'LONG').upper()
    side = 'BUY' if direction == 'LONG' else 'SELL'

    order_plan = {
        'side': side,
        'entry_price': float(payload.get('entry_price') or 0.0),
        'leverage': int(payload.get('leverage') or 1),
        'order_type': 'LIMIT',
    }

    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base = Path(output_dir) if output_dir is not None else Path('artifacts/trading')
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / f'a5_execution_{ts}.json'

    result = {
        'stage_id': 'A5',
        'trace_id': payload.get('trace_id'),
        'direction': direction,
        'order_plan': order_plan,
        'timestamp': ts,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result['artifact_path'] = str(out_path)
    return result
