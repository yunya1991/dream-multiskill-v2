"""TripleScreenAligner: V5 三屏信号对齐。

基于 qmm-v5-vision.md Section 3.3.1 设计。
将记忆信号与技术信号融合，检测共振状态。
"""

from typing import Any, Dict, List

import numpy as np


class TripleScreenAligner:
    """记忆信号 + 三屏交易系统融合。

    原理: 多周期信号共振 = 更强信号。
    三屏: week(长期), day(中期), hour(短期)。
    """

    def __init__(self):
        self.screens = {
            "week": {"weight": 0.4, "lookback_pct": 0.6},
            "day": {"weight": 0.35, "lookback_pct": 0.35},
            "hour": {"weight": 0.25, "lookback_pct": 0.15},
        }

    def align(
        self,
        events: List[Any],  # QMMEvent list
    ) -> Dict[str, Any]:
        """三屏信号对齐。

        基于时间衰减将事件分为长/中/短期窗口，
        计算各屏方向分数，加权融合。

        Returns:
            {
                "direction": "UP" / "DOWN" / "NEUTRAL",
                "score": float (0-1),
                "resonance_status": str,
                "screen_signals": dict,
            }
        """
        if not events:
            return self._neutral_result()

        # 计算各屏信号
        screen_signals = {}
        for screen_name, config in self.screens.items():
            # 简单划分：按时间顺序分三段
            n = len(events)
            if screen_name == "week":
                window = events[:int(n * 0.6)]
            elif screen_name == "day":
                window = events[int(n * 0.3):int(n * 0.8)]
            else:
                window = events[int(n * 0.7):]

            if not window:
                screen_signals[screen_name] = {
                    "direction": "NEUTRAL", "confidence": 0,
                    "x_mean": 0, "y_mean": 0, "profit_rate": 0,
                }
                continue

            x_mean = np.mean([e.quadrant_x for e in window])
            y_mean = np.mean([e.quadrant_y for e in window])
            profits = sum(1 for e in window if e.is_profit is True)
            profit_rate = profits / len(window)

            if x_mean > 0.1:
                direction = "UP"
            elif x_mean < -0.1:
                direction = "DOWN"
            else:
                direction = "NEUTRAL"

            confidence = y_mean * min(1.0, len(window) / 20)
            confidence = max(0, min(1, confidence))

            screen_signals[screen_name] = {
                "direction": direction,
                "confidence": round(confidence, 4),
                "x_mean": round(x_mean, 4),
                "y_mean": round(y_mean, 4),
                "profit_rate": round(profit_rate, 4),
            }

        # 加权融合
        weighted_direction = 0.0
        total_weight = 0.0
        for screen_name, config in self.screens.items():
            sig = screen_signals[screen_name]
            dir_map = {"UP": 1, "DOWN": -1, "NEUTRAL": 0}
            weighted_direction += dir_map[sig["direction"]] * config["weight"]
            total_weight += config["weight"]

        final_score = weighted_direction / max(total_weight, 0.01)

        # 方向判断
        if final_score > 0.2:
            direction = "UP"
        elif final_score < -0.2:
            direction = "DOWN"
        else:
            direction = "NEUTRAL"

        # 共振检测
        resonance = self._detect_resonance(screen_signals)

        return {
            "direction": direction,
            "score": round(abs(final_score), 4),
            "resonance_status": resonance,
            "screen_signals": screen_signals,
        }

    def _detect_resonance(self, screen_signals: Dict[str, Dict]) -> str:
        """检测共振状态。"""
        directions = []
        for s in ["week", "day", "hour"]:
            sig = screen_signals.get(s, {})
            directions.append(sig.get("direction", "NEUTRAL"))

        # 去除 NEUTRAL
        active = [d for d in directions if d != "NEUTRAL"]

        if not active:
            return "NO_SIGNAL"

        agree_count = active.count(active[0])
        total = len(active)

        if agree_count == total and total >= 3:
            return "STRONG_RESONANCE"
        elif agree_count >= 2 and total >= 2:
            return "WEAK_RESONANCE"
        elif agree_count < total / 2:
            return "DIVERGENCE"
        else:
            return "MIXED"

    def _neutral_result(self) -> Dict[str, Any]:
        return {
            "direction": "NEUTRAL",
            "score": 0,
            "resonance_status": "NO_SIGNAL",
            "screen_signals": {},
        }
