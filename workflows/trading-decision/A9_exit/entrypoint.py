import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _exit_action(unrealized_pnl_pct: float, risk_level: str) -> str:
    risk = (risk_level or '').lower()
    if unrealized_pnl_pct >= 3.0:
        return 'TAKE_PROFIT'
    if unrealized_pnl_pct <= -2.0 or risk in {'high', 'extreme'}:
        return 'STOP_LOSS'
    return 'HOLD'


def run_a9_exit(payload: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Thin wrapper for A9 exit plan output."""
    pnl = float(payload.get('unrealized_pnl_pct') or 0.0)
    risk_level = str(payload.get('risk_level') or 'medium')
    action = _exit_action(unrealized_pnl_pct=pnl, risk_level=risk_level)

    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base = Path(output_dir) if output_dir is not None else Path('artifacts/trading')
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / f'a9_exit_{ts}.json'

    result = {
        'stage_id': 'A9',
        'trace_id': payload.get('trace_id'),
        'unrealized_pnl_pct': pnl,
        'risk_level': risk_level,
        'exit_action': action,
        'timestamp': ts,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result['artifact_path'] = str(out_path)
    return result
