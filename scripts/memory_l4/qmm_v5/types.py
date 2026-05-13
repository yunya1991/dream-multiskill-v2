"""V5 数据类型。"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QMMEvent:
    """从 TradeCase 提取的量化事件。"""
    event_id: str
    ts: str
    regime: str
    pnl_pct: Optional[float]
    is_profit: Optional[bool]
    quadrant_x: float
    quadrant_y: float
    y_perf: float
    y_consistency: float
    y_human: float
    stage_coverage: List[str] = field(default_factory=list)
    stages_count: int = 0
    pnl_usdt: Optional[float] = None
    drawdown: Optional[float] = None
    exit_reason: Optional[str] = None
    time_decay: float = 1.0

    def to_feature_vector(self) -> List[float]:
        """编码为数值特征向量。

        12 维特征（不含 pnl_pct / direction，避免数据泄露）：
        0: quadrant_x
        1: quadrant_y
        2: y_perf
        3: y_consistency
        4: y_human
        5: stage_coverage A0
        6: stage_coverage A5
        7: stage_coverage A9
        8: stages_count / 10
        9: time_decay
        10: regime encoded
        11: drawdown
        """
        regime_map = {
            "bull": 1.0, "bear": -1.0, "oscillation": 0.0,
            "crash": -2.0, "recovery": 0.5, "consolidation": 0.2,
        }
        return [
            self.quadrant_x,
            self.quadrant_y,
            self.y_perf,
            self.y_consistency,
            self.y_human,
            self.stage_coverage.count("A0"),
            self.stage_coverage.count("A5"),
            self.stage_coverage.count("A9"),
            self.stages_count / 10.0,
            self.time_decay,
            regime_map.get(self.regime, 0.0),
            self.drawdown if self.drawdown is not None else 0.0,
        ]


@dataclass
class GateResultV5:
    passed: bool
    reason_codes: List[str] = field(default_factory=list)
    ml_accuracy: float = 0.0
    baseline_accuracy: float = 0.0
    train_test_gap: float = 0.0
    fold_accuracies: List[float] = field(default_factory=list)
    overfitting: bool = False
    drift_detected: bool = False

    def recommendation(self) -> str:
        if self.passed:
            return "RADICAL — ML significantly outperforms deterministic baseline"
        return "CONSERVATIVE — proceed with V2→V3→V4 phased approach"
