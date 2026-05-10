import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _pick_strategy_mode(signal_score: float, volatility: float, market_regime: str) -> str:
    regime = (market_regime or '').lower()
    if signal_score >= 60 and volatility <= 0.03 and regime in {'trend', 'breakout'}:
        return 'trend_follow'
    if volatility >= 0.04 or regime in {'range', 'chop'}:
        return 'mean_revert'
    return 'neutral'


def run_a3_simulation(payload: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Thin wrapper for A3 strategy simulation artifact output."""
    signal_score = float(payload.get('signal_score') or 50.0)
    volatility = float(payload.get('volatility') or 0.02)
    market_regime = str(payload.get('market_regime') or 'neutral')
    strategy_mode = _pick_strategy_mode(signal_score, volatility, market_regime)

    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base = Path(output_dir) if output_dir is not None else Path('artifacts/trading')
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / f'a3_simulation_{ts}.json'

    result = {
        'stage_id': 'A3',
        'trace_id': payload.get('trace_id'),
        'signal_score': signal_score,
        'volatility': volatility,
        'market_regime': market_regime,
        'strategy_mode': strategy_mode,
        'timestamp': ts,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result['artifact_path'] = str(out_path)
    return result
