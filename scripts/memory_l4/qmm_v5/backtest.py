"""Walk-Forward 回测框架 (V5)。

执行 walk-forward 交叉验证，比较 ML 模型与确定性基线。
用于 Phase A 收敛判断。
"""

from typing import Any, Dict, List, Tuple

import numpy as np

from .types import QMMEvent, GateResultV5


class V5Backtester:
    """V5 Walk-Forward 回测执行器。

    同时运行 ML 模型和确定性基线，比较准确率。
    """

    def __init__(
        self,
        n_folds: int = 5,
        min_train: int = 15,
        min_test: int = 5,
    ):
        self.n_folds = n_folds
        self.min_train = min_train
        self.min_test = min_test

    def run(
        self,
        feature_matrix: np.ndarray,
        events: List[QMMEvent],
    ) -> GateResultV5:
        """执行 walk-forward 回测。

        Args:
            feature_matrix: (N x 14) 特征矩阵
            events: QMMEvent 列表（与 feature_matrix 对应）

        Returns:
            GateResultV5 包含 ML vs 基线比较
        """
        # 标签
        y = np.array(
            [1 if ev.pnl_pct is not None and ev.pnl_pct > 0 else 0
             for ev in events],
            dtype=int,
        )
        valid_mask = np.array([ev.pnl_pct is not None for ev in events])
        X_valid = feature_matrix[valid_mask]
        y_valid = y[valid_mask]

        if len(X_valid) < self.min_train + self.min_test:
            return GateResultV5(
                passed=False,
                reason_codes=["INSUFFICIENT_DATA_FOR_BACKTEST"],
                ml_accuracy=0.0,
                baseline_accuracy=0.0,
            )

        folds = self._split_folds(len(X_valid))
        ml_corrects = 0
        ml_total = 0
        baseline_corrects = 0
        baseline_total = 0
        fold_ml_acc = []
        fold_bl_acc = []

        for train_idx, test_idx in folds:
            X_train, X_test = X_valid[train_idx], X_valid[test_idx]
            y_train, y_test = y_valid[train_idx], y_valid[test_idx]

            # ML 预测
            ml_preds = self._train_and_predict(X_train, y_train, X_test)
            ml_correct = sum(1 for p, a in zip(ml_preds, y_test) if p == a)
            ml_corrects += ml_correct
            ml_total += len(y_test)
            fold_ml_acc.append(ml_correct / max(len(y_test), 1))

            # 确定性基线预测
            bl_preds = self._baseline_predict(X_test)
            bl_correct = sum(1 for p, a in zip(bl_preds, y_test) if p == a)
            baseline_corrects += bl_correct
            baseline_total += len(y_test)
            fold_bl_acc.append(bl_correct / max(len(y_test), 1))

        ml_accuracy = ml_corrects / max(ml_total, 1)
        baseline_accuracy = baseline_corrects / max(baseline_total, 1)

        # Train/test gap
        train_acc = self._train_accuracy_estimate(folds, X_valid, y_valid)
        train_test_gap = max(0, train_acc - ml_accuracy)

        # 过拟合检测
        overfitting = train_test_gap > 0.15
        if len(fold_ml_acc) >= 2:
            fold_var = float(np.var(fold_ml_acc))
            overfitting = overfitting or fold_var > 0.02

        # 判断：ML 显著优于基线
        improvement = ml_accuracy - baseline_accuracy
        passed = (
            ml_accuracy > 0.55
            and improvement > 0.05
            and not overfitting
        )

        reason_codes = []
        if ml_accuracy <= 0.55:
            reason_codes.append("ML_ACCURACY_TOO_LOW")
        if improvement <= 0.05:
            reason_codes.append("ML_NOT_SIGNIFICANTLY_BETTER_BASELINE")
        if overfitting:
            reason_codes.append("OVERFITTING_DETECTED")

        return GateResultV5(
            passed=passed,
            reason_codes=reason_codes,
            ml_accuracy=round(ml_accuracy, 4),
            baseline_accuracy=round(baseline_accuracy, 4),
            train_test_gap=round(train_test_gap, 4),
            fold_accuracies=[round(a, 4) for a in fold_ml_acc],
            overfitting=overfitting,
            drift_detected=False,  # 需要更多数据才能检测漂移
        )

    def _split_folds(self, n: int) -> List[Tuple[List[int], List[int]]]:
        """扩展窗口分割。"""
        min_total = self.min_train + self.min_test
        if n < min_total:
            return []

        fold_size = max((n - self.min_train) // self.n_folds, self.min_test)
        folds = []
        for i in range(self.n_folds):
            train_end = self.min_train + i * fold_size
            test_end = min(train_end + fold_size, n)
            if test_end - train_end < self.min_test:
                break
            folds.append((
                list(range(train_end)),
                list(range(train_end, test_end)),
            ))
        return folds

    def _train_and_predict(
        self, X_train: np.ndarray, y_train: np.ndarray,
        X_test: np.ndarray,
    ) -> np.ndarray:
        """训练 GradientBoosting 并预测。

        固定 random_state 保证可复现。
        """
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        n_up = sum(y_train)
        n_down = len(y_train) - n_up

        # 如果类别不平衡太严重，退化为多数类
        if n_up == 0 or n_down == 0:
            return np.full(len(X_test), 1 if n_up > 0 else 0)

        model = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=2,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X_train_scaled, y_train)
        return model.predict(X_test_scaled)

    def _baseline_predict(self, X_test: np.ndarray) -> np.ndarray:
        """确定性基线：用 quadrant_x 方向预测。

        与 V2 baseline 保持一致：x>0 → UP, x<0 → DOWN。
        """
        quadrant_x = X_test[:, 0]  # 第 0 维 = quadrant_x
        preds = np.where(quadrant_x > 0.1, 1,
                         np.where(quadrant_x < -0.1, 0, 1))
        return preds

    def _train_accuracy_estimate(
        self,
        folds: List[Tuple[List[int], List[int]]],
        X: np.ndarray, y: np.ndarray,
    ) -> float:
        """估算 train 准确率（取最后一个 fold 的 train 集）。"""
        if not folds:
            return 0.0
        last_train_idx = folds[-1][0]
        if not last_train_idx:
            return 0.0
        X_train = X[last_train_idx]
        y_train = y[last_train_idx]
        preds = self._train_and_predict(X_train, y_train, X_train)
        return sum(1 for p, a in zip(preds, y_train) if p == a) / max(len(y_train), 1)
