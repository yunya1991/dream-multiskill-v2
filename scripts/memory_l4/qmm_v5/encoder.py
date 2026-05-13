"""EventEncoder: 将 TradeCase 编码为数值特征向量 (V5)。

基于 qmm-v5-vision.md Section 3.2.1 设计。
使用 numpy 进行向量化编码。
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .types import QMMEvent


class EventEncoder:
    """将记忆事件编码为数值向量。

    特征维度 = 实际特征数（非固定 128 维）：
    1. quadrant_x (-1 ~ 1)
    2. quadrant_y (0 ~ 1)
    3. pnl_pct
    4. y_perf (0 ~ 1)
    5. y_consistency (0 ~ 1)
    6. y_human (0 ~ 1)
    7. stage_coverage A0
    8. stage_coverage A5
    9. stage_coverage A9
    10. stages_count / 10
    11. time_decay (0 ~ 1)
    12. regime encoded
    13. direction (+1/-1/0)
    14. drawdown
    """

    FEATURE_DIM = 14
    HALF_LIFE_DAYS = 69  # e^{-0.01 * days} ≈ 69 天半衰期

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def encode(self, case: Dict[str, Any]) -> Optional[QMMEvent]:
        """从单个 TradeCase 提取并编码事件。"""
        do = case.get("decision_outcome") or {}
        q = case.get("quadrant") or {}
        env = case.get("environment_snapshot") or {}

        pnl = do.get("pnl_pct")
        ts = case.get("ts_start", "")

        # 时间衰减
        time_decay = self._time_decay(ts)

        # 从 thinking_chain 提取 stage 覆盖
        stages = self._extract_stages(case)

        return QMMEvent(
            event_id=case.get("case_id", ""),
            ts=ts,
            regime=env.get("regime", "unknown"),
            pnl_pct=float(pnl) if pnl is not None else None,
            is_profit=(pnl > 0) if pnl is not None else None,
            quadrant_x=float(q.get("x", 0)),
            quadrant_y=float(q.get("y", 0)),
            y_perf=float(q.get("evidence", {}).get("y_perf", 0)),
            y_consistency=float(q.get("evidence", {}).get("y_consistency", 0)),
            y_human=float(q.get("evidence", {}).get("y_human", 0)),
            stage_coverage=stages,
            stages_count=len(stages),
            pnl_usdt=do.get("pnl_usdt"),
            drawdown=do.get("drawdown"),
            exit_reason=do.get("exit_reason"),
            time_decay=time_decay,
        )

    def encode_batch(
        self, cases: List[Dict[str, Any]]
    ) -> List[QMMEvent]:
        """批量编码，跳过无效 case。"""
        events = []
        for c in cases:
            ev = self.encode(c)
            if ev is not None:
                events.append(ev)
        return events

    def to_numpy(self, events: List[QMMEvent]) -> np.ndarray:
        """将事件列表转为 numpy 特征矩阵 (N x 14)。"""
        vectors = [e.to_feature_vector() for e in events]
        return np.array(vectors, dtype=np.float64)

    def _time_decay(self, ts: str) -> float:
        """时间衰减: e^{-0.01 * days_old}。"""
        if not ts:
            return 0.0
        try:
            from datetime import datetime, timezone
            parsed = datetime.fromisoformat(ts)
            now = datetime.now(timezone.utc)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            days_old = max(0, (now - parsed).total_seconds() / 86400)
            return math.exp(-0.01 * days_old)
        except (ValueError, TypeError):
            return 0.0

    def _extract_stages(self, case: Dict[str, Any]) -> List[str]:
        """从 thinking_chain 提取 A0-A9 覆盖。"""
        chain = case.get("thinking_chain") or []
        stages = set()
        for entry in chain:
            s = entry.get("stage")
            if s and s.startswith("A") and len(s) <= 3:
                stages.add(s)
        return sorted(stages)
