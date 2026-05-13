"""MemoryTrainer: sklearn 方向预测训练器 (V5)。

基于 qmm-v5-vision.md Section 3.4.1 设计。
使用 GradientBoostingClassifier 进行方向预测。
固定 random_state 保证可复现。
"""

from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler


class MemoryTrainer:
    """基于历史 TradeCase 训练方向预测模型。

    特征: quadrant_x, quadrant_y, pnl_pct, y_perf, y_consistency, y_human,
           stage coverage, time_decay, regime, drawdown
    标签: direction (1=UP, 0=DOWN)
    模型: GradientBoostingClassifier
    """

    RANDOM_STATE = 42

    def __init__(self):
        self.model: Optional[GradientBoostingClassifier] = None
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self._is_fitted = False

    def prepare_data(
        self, feature_matrix: np.ndarray, events: List[Any],
    ) -> tuple:
        """准备训练数据。

        Returns:
            (X_scaled, y, feature_names)
            X_scaled: 标准化后的特征矩阵
            y: 方向标签 (1=UP if pnl>0 else 0)
        """
        # 标签: pnl > 0 → UP(1), else DOWN(0)
        y = np.array(
            [1 if ev.pnl_pct is not None and ev.pnl_pct > 0 else 0
             for ev in events],
            dtype=int,
        )

        # 过滤没有 pnl 的样本
        valid_mask = np.array([ev.pnl_pct is not None for ev in events])
        X = feature_matrix[valid_mask]
        y = y[valid_mask]

        # 标准化
        if len(X) > 0:
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = X

        self.feature_names = [
            "quadrant_x", "quadrant_y", "pnl_pct",
            "y_perf", "y_consistency", "y_human",
            "stage_a0", "stage_a5", "stage_a9",
            "stage_coverage_pct", "time_decay", "regime",
            "direction", "drawdown",
        ]

        return X_scaled, y

    def train(
        self, X: np.ndarray, y: np.ndarray,
    ) -> Dict[str, Any]:
        """训练模型并返回训练指标。

        Args:
            X: 标准化特征矩阵 (N x 14)
            y: 标签 (N,)

        Returns:
            {
                "train_accuracy": float,
                "cv_accuracy_mean": float,
                "cv_accuracy_std": float,
                "feature_importances": dict,
                "n_samples": int,
            }
        """
        if len(X) < 5:
            return {
                "train_accuracy": 0.0,
                "cv_accuracy_mean": 0.0,
                "cv_accuracy_std": 0.0,
                "feature_importances": {},
                "n_samples": len(X),
                "error": "INSUFFICIENT_DATA",
            }

        self.model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            random_state=self.RANDOM_STATE,
        )
        self.model.fit(X, y)
        self._is_fitted = True

        train_accuracy = self.model.score(X, y)

        # 交叉验证
        cv_folds = min(3, min(sum(y), len(y) - sum(y)))
        if cv_folds >= 2:
            cv_scores = cross_val_score(
                self.model, X, y, cv=cv_folds, scoring="accuracy",
            )
            cv_mean = float(cv_scores.mean())
            cv_std = float(cv_scores.std())
        else:
            cv_mean = 0.0
            cv_std = 0.0

        # 特征重要性
        feature_importances = {}
        if self.feature_names and hasattr(self.model, "feature_importances_"):
            for name, imp in zip(
                self.feature_names, self.model.feature_importances_,
            ):
                feature_importances[name] = round(float(imp), 4)

        return {
            "train_accuracy": round(train_accuracy, 4),
            "cv_accuracy_mean": round(cv_mean, 4),
            "cv_accuracy_std": round(cv_std, 4),
            "feature_importances": feature_importances,
            "n_samples": len(X),
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测方向。"""
        if not self._is_fitted or self.model is None:
            raise RuntimeError("Model not trained yet")
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率。"""
        if not self._is_fitted or self.model is None:
            raise RuntimeError("Model not trained yet")
        return self.model.predict_proba(X)

    def predict_direction(self, X: np.ndarray) -> List[str]:
        """预测方向标签。"""
        preds = self.predict(X)
        return ["UP" if p == 1 else "DOWN" for p in preds]
