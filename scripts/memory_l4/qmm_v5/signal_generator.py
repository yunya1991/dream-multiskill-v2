"""SignalGenerator: 从记忆向量生成趋势信号 (V5)。

基于 qmm-v5-vision.md Section 3.2.3 设计。
核心: 趋势 = 记忆向量的时间加权方向。
"""

from typing import Any, Dict, List

import numpy as np


class SignalGenerator:
    """从记忆向量生成趋势信号。"""

    def __init__(self):
        # 事件类型权重（用于加权聚合）
        self.regime_weights = {
            "bull": 0.15,
            "bear": 0.15,
            "oscillation": 0.1,
            "crash": 0.2,
            "recovery": 0.15,
            "consolidation": 0.1,
            "unknown": 0.05,
        }

    def generate_signal(
        self,
        feature_matrix: np.ndarray,
        events: List[Any],  # QMMEvent list
    ) -> Dict[str, Any]:
        """生成趋势信号。

        Args:
            feature_matrix: (N x 12) numpy 矩阵
            events: 对应的 QMMEvent 列表

        Returns:
            {
                "direction": "UP" / "DOWN" / "NEUTRAL",
                "confidence": float (0-1),
                "strength": float,
                "weighted_mean_vector": np.ndarray,
            }
        """
        if len(feature_matrix) == 0:
            return {
                "direction": "NEUTRAL", "confidence": 0,
                "strength": 0, "weighted_mean_vector": None,
            }

        # Step 1: 时间加权
        weights = np.array([ev.time_decay for ev in events], dtype=np.float64)
        weights /= weights.sum()

        # Step 2: 加权平均向量
        weighted_mean = np.average(feature_matrix, axis=0, weights=weights)

        # Step 3: 方向判断（用 quadrant_x 维度）
        direction_score = weighted_mean[0]  # index 0 = quadrant_x

        # Step 4: 强度
        strength = float(np.linalg.norm(weighted_mean[:4]))  # 前 4 维

        # Step 5: 置信度
        n_events = len(events)
        data_factor = min(1.0, n_events / 20)
        avg_time_decay = float(np.mean(weights)) * n_events
        confidence = min(1.0, abs(direction_score) * data_factor * (0.5 + 0.5 * avg_time_decay))

        if direction_score > 0.1:
            direction = "UP"
        elif direction_score < -0.1:
            direction = "DOWN"
        else:
            direction = "NEUTRAL"

        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "strength": round(strength, 4),
            "direction_score": round(direction_score, 4),
            "weighted_mean_vector": weighted_mean,
        }
