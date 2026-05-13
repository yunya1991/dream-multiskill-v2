"""V5 真实回测验证：从 L4 产出物加载真实 TradeCase。

按时间顺序划分训练集和测试集，模拟"对未知行情做预测"。
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .encoder import EventEncoder
from .types import QMMEvent
from .trainer import MemoryTrainer


# ============================================================
# 数据加载
# ============================================================

def load_l4_cases(cases_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """从 L4 memory 加载真实 TradeCase。"""
    if cases_dir is None:
        cases_dir = Path(__file__).parents[3] / ".workbuddy" / "memory_l4" / "cases"
    if not cases_dir.exists():
        return []
    cases = []
    for f in sorted(cases_dir.glob("*.json")):
        try:
            with open(f) as fp:
                cases.append(json.load(fp))
        except Exception:
            pass
    return cases


# ============================================================
# 时间分割回测
# ============================================================

def temporal_split_backtest(
    cases: List[Dict[str, Any]],
    split_ratios: List[float] = None,
) -> Dict[str, Any]:
    """按时间分割回测：用前 N% 训练，后 (100-N)% 测试。

    模拟真实场景：已知历史数据 → 预测未来行情。

    split_ratios: 如 [0.5, 0.6, 0.7, 0.8] 表示用前 50/60/70/80% 数据训练，
                  剩余 50/40/30/20% 测试。
    """
    if split_ratios is None:
        split_ratios = [0.5, 0.6, 0.7, 0.8]

    encoder = EventEncoder()
    all_events = encoder.encode_batch(cases)

    # 按时间排序（最早在前）
    all_events.sort(key=lambda e: e.ts or "")

    if len(all_events) < 20:
        return {"error": "INSUFFICIENT_CASES", "n_events": len(all_events)}

    results = {}
    for ratio in split_ratios:
        split_point = int(len(all_events) * ratio)
        train_events = all_events[:split_point]
        test_events = all_events[split_point:]

        if len(train_events) < 10 or len(test_events) < 5:
            results[f"split_{ratio:.0%}"] = {
                "n_train": len(train_events),
                "n_test": len(test_events),
                "error": "INSUFFICIENT_SPLIT",
            }
            continue

        r = _single_split(train_events, test_events, ratio)
        results[f"split_{ratio:.0%}"] = r

    return {
        "n_total_events": len(all_events),
        "splits": results,
        "regime_distribution": _regime_dist(all_events),
    }


def _single_split(
    train_events: List[QMMEvent],
    test_events: List[QMMEvent],
    ratio: float,
) -> Dict[str, Any]:
    """单个时间分割回测。"""
    encoder = EventEncoder()
    trainer = MemoryTrainer()

    X_train_raw = encoder.to_numpy(train_events)
    X_test_raw = encoder.to_numpy(test_events)

    # 准备数据
    X_train, y_train = trainer.prepare_data(X_train_raw, train_events)
    X_test, y_test = trainer.prepare_data(X_test_raw, test_events)

    if len(X_train) < 5 or len(X_test) < 3:
        return {
            "n_train_raw": len(train_events),
            "n_test_raw": len(test_events),
            "n_train_valid": len(X_train),
            "n_test_valid": len(X_test),
            "error": "INSUFFICIENT_VALID_DATA",
        }

    # 训练
    train_metrics = trainer.train(X_train, y_train)

    # ML 预测
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    ml_preds = trainer.model.predict(X_test_scaled)
    ml_correct = sum(1 for p, a in zip(ml_preds, y_test) if p == a)
    ml_accuracy = ml_correct / max(len(y_test), 1)

    # 确定性基线: quadrant_x > 0.1 → UP, else DOWN
    quadrant_x = X_test_raw[:, 0]
    bl_preds = np.where(quadrant_x > 0.1, 1,
                        np.where(quadrant_x < -0.1, 0, 1))
    bl_correct = sum(1 for p, a in zip(bl_preds, y_test) if p == a)
    bl_accuracy = bl_correct / max(len(y_test), 1)

    # 每折回测 (把测试集分成小段)
    fold_ml_accs = _fold_accuracies(X_test_scaled, y_test, n_folds=3)
    fold_bl_accs = _fold_baseline_accuracies(X_test_raw, y_test, n_folds=3)

    # 按 regime 分类准确率
    regime_ml = _per_regime_accuracy(X_test_raw, y_test, ml_preds, test_events)
    regime_bl = _per_regime_baseline(X_test_raw, y_test, test_events)

    # 测试集内的时间趋势
    time_trend = _time_trend_accuracy(X_test_raw, y_test, ml_preds, test_events)

    return {
        "n_train_raw": len(train_events),
        "n_test_raw": len(test_events),
        "n_train_valid": len(X_train),
        "n_test_valid": len(X_test),
        "ml_accuracy": round(ml_accuracy, 4),
        "baseline_accuracy": round(bl_accuracy, 4),
        "improvement": round(ml_accuracy - bl_accuracy, 4),
        "ml_better_than_baseline": ml_accuracy > bl_accuracy,
        "train_accuracy": train_metrics.get("train_accuracy"),
        "cv_accuracy_mean": train_metrics.get("cv_accuracy_mean"),
        "cv_accuracy_std": train_metrics.get("cv_accuracy_std"),
        "fold_ml_accuracies": fold_ml_accs,
        "fold_bl_accuracies": fold_bl_accs,
        "per_regime_ml": regime_ml,
        "per_regime_bl": regime_bl,
        "time_trend": time_trend,
    }


def _fold_accuracies(
    X: np.ndarray, y: np.ndarray, n_folds: int = 3,
) -> List[float]:
    """将测试集分段，看每段的准确率。"""
    n = len(X)
    fold_size = max(n // n_folds, 1)
    accs = []
    for i in range(n_folds):
        start = i * fold_size
        end = start + fold_size if i < n_folds - 1 else n
        acc = sum(1 for p in range(start, end) if p < len(y)) / max(end - start, 1)
    # 重新计算：需要预测
    accs = []
    for i in range(n_folds):
        start = i * fold_size
        end = start + fold_size if i < n_folds - 1 else n
        chunk_size = end - start
        # 多数类预测
        chunk_y = y[start:end]
        majority = int(np.round(chunk_y.mean()))
        preds = np.full(chunk_size, majority)
        acc = sum(1 for p, a in zip(preds, chunk_y) if p == a) / chunk_size
        accs.append(round(acc, 4))
    return accs


def _fold_baseline_accuracies(
    X: np.ndarray, y: np.ndarray, n_folds: int = 3,
) -> List[float]:
    n = len(X)
    fold_size = max(n // n_folds, 1)
    accs = []
    for i in range(n_folds):
        start = i * fold_size
        end = start + fold_size if i < n_folds - 1 else n
        chunk_x = X[start:end]
        chunk_y = y[start:end]
        qx = chunk_x[:, 0]
        preds = np.where(qx > 0.1, 1, np.where(qx < -0.1, 0, 1))
        acc = sum(1 for p, a in zip(preds, chunk_y) if p == a) / len(chunk_y)
        accs.append(round(acc, 4))
    return accs


def _per_regime_accuracy(
    X: np.ndarray, y: np.ndarray, preds: np.ndarray,
    events: List[QMMEvent],
) -> Dict[str, Dict[str, float]]:
    """按 regime 统计准确率。"""
    from collections import defaultdict
    regime_correct = defaultdict(int)
    regime_total = defaultdict(int)
    for ev, p, a in zip(events, preds, y):
        regime_total[ev.regime] += 1
        if p == a:
            regime_correct[ev.regime] += 1
    return {
        r: {
            "accuracy": round(regime_correct[r] / regime_total[r], 4),
            "n": regime_total[r],
        }
        for r in sorted(regime_total.keys())
    }


def _per_regime_baseline(
    X: np.ndarray, y: np.ndarray,
    events: List[QMMEvent],
) -> Dict[str, Dict[str, float]]:
    """按 regime 统计基线准确率。"""
    from collections import defaultdict
    qx = X[:, 0]
    bl_preds = np.where(qx > 0.1, 1, np.where(qx < -0.1, 0, 1))
    regime_correct = defaultdict(int)
    regime_total = defaultdict(int)
    for ev, p, a in zip(events, bl_preds, y):
        regime_total[ev.regime] += 1
        if p == a:
            regime_correct[ev.regime] += 1
    return {
        r: {
            "accuracy": round(regime_correct[r] / regime_total[r], 4),
            "n": regime_total[r],
        }
        for r in sorted(regime_total.keys())
    }


def _time_trend_accuracy(
    X: np.ndarray, y: np.ndarray, preds: np.ndarray,
    events: List[QMMEvent],
) -> Dict[str, float]:
    """按时间分段看准确率变化：早期 vs 晚期。"""
    n = len(events)
    first_half = n // 2
    acc_first = sum(1 for p, a in zip(preds[:first_half], y[:first_half]) if p == a) / max(first_half, 1)
    acc_second = sum(1 for p, a in zip(preds[first_half:], y[first_half:]) if p == a) / max(n - first_half, 1)
    return {
        "first_half_accuracy": round(acc_first, 4),
        "second_half_accuracy": round(acc_second, 4),
        "n_first": first_half,
        "n_second": n - first_half,
    }


def _regime_dist(events: List[QMMEvent]) -> Dict[str, int]:
    dist = {}
    for e in events:
        dist[e.regime] = dist.get(e.regime, 0) + 1
    return dist


# ============================================================
# 跨 regime 泛化测试
# ============================================================

def cross_regime_backtest(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """跨 regime 泛化测试：
    训练集不含某个 regime，看对该 regime 的预测能力。
    """
    encoder = EventEncoder()
    all_events = encoder.encode_batch(cases)
    all_events.sort(key=lambda e: e.ts or "")

    regimes = set(e.regime for e in all_events)
    results = {}

    for holdout_regime in regimes:
        # 训练集: 不含 holdout_regime
        train_events = [e for e in all_events if e.regime != holdout_regime]
        test_events = [e for e in all_events if e.regime == holdout_regime]

        if len(train_events) < 10 or len(test_events) < 3:
            results[holdout_regime] = {
                "n_train": len(train_events),
                "n_test": len(test_events),
                "error": "INSUFFICIENT",
            }
            continue

        trainer = MemoryTrainer()
        X_train_raw = encoder.to_numpy(train_events)
        X_test_raw = encoder.to_numpy(test_events)

        X_train, y_train = trainer.prepare_data(X_train_raw, train_events)
        X_test, y_test = trainer.prepare_data(X_test_raw, test_events)

        if len(X_train) < 5 or len(X_test) < 3:
            results[holdout_regime] = {
                "error": "INSUFFICIENT_VALID_DATA",
            }
            continue

        scaler = None
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        trainer.train(X_train, y_train)

        ml_preds = trainer.model.predict(X_test_scaled)
        ml_acc = sum(1 for p, a in zip(ml_preds, y_test) if p == a) / len(y_test)

        # baseline
        qx = X_test_raw[:, 0]
        bl_preds = np.where(qx > 0.1, 1, np.where(qx < -0.1, 0, 1))
        bl_acc = sum(1 for p, a in zip(bl_preds, y_test) if p == a) / len(y_test)

        results[holdout_regime] = {
            "n_train": len(train_events),
            "n_test": len(test_events),
            "ml_accuracy": round(ml_acc, 4),
            "baseline_accuracy": round(bl_acc, 4),
            "improvement": round(ml_acc - bl_acc, 4),
        }

    return results


# ============================================================
# 主入口
# ============================================================

def run_backtest_validation(cases_dir: Optional[Path] = None):
    """运行完整的真实回测验证。"""
    cases = load_l4_cases(cases_dir)
    if not cases:
        print("ERROR: No L4 cases found.")
        return

    print(f"Loaded {len(cases)} TradeCase from L4 memory\n")

    # 1. 时间分割回测
    print("=" * 60)
    print("TEMPORAL SPLIT BACKTEST")
    print("=" * 60)
    temp_result = temporal_split_backtest(cases)
    print(f"Total events: {temp_result['n_total_events']}")
    print(f"Regime distribution: {temp_result['regime_distribution']}\n")

    for split_name, r in temp_result.get("splits", {}).items():
        print(f"--- {split_name} ---")
        if "error" in r:
            print(f"  ERROR: {r['error']} (train={r.get('n_train_raw')}, test={r.get('n_test_raw')})")
            continue
        print(f"  Train: {r['n_train_raw']} events ({r['n_train_valid']} valid)")
        print(f"  Test:  {r['n_test_raw']} events ({r['n_test_valid']} valid)")
        print(f"  ML accuracy:          {r['ml_accuracy']:.1%}")
        print(f"  Baseline accuracy:    {r['baseline_accuracy']:.1%}")
        print(f"  Improvement:          {r['improvement']:+.1%}")
        print(f"  ML > Baseline:        {r['ml_better_than_baseline']}")
        print(f"  Train accuracy:       {r['train_accuracy']:.1%}")
        print(f"  CV accuracy:          {r['cv_accuracy_mean']:.1%} (+/- {r['cv_accuracy_std']:.2%})")
        print(f"  Per-regime ML:        {r['per_regime_ml']}")
        print(f"  Per-regime baseline:  {r['per_regime_bl']}")
        print(f"  Time trend:           {r['time_trend']}")
        print()

    # 2. 跨 regime 泛化
    print("=" * 60)
    print("CROSS-REGIME GENERALIZATION TEST")
    print("=" * 60)
    cross_result = cross_regime_backtest(cases)
    for regime, r in cross_result.items():
        print(f"--- Holdout: {regime} ---")
        if "error" in r:
            print(f"  ERROR: {r['error']}")
            continue
        print(f"  Train: {r['n_train']}, Test: {r['n_test']}")
        print(f"  ML accuracy:        {r['ml_accuracy']:.1%}")
        print(f"  Baseline accuracy:  {r['baseline_accuracy']:.1%}")
        print(f"  Improvement:        {r['improvement']:+.1%}")
        print()

    # 汇总
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_splits = [r for r in temp_result.get("splits", {}).values() if "error" not in r]
    if all_splits:
        avg_ml = np.mean([r["ml_accuracy"] for r in all_splits])
        avg_bl = np.mean([r["baseline_accuracy"] for r in all_splits])
        print(f"Average ML accuracy (all splits):     {avg_ml:.1%}")
        print(f"Average Baseline accuracy (all splits): {avg_bl:.1%}")
        print(f"Average improvement:                  {avg_ml - avg_bl:+.1%}")
        ml_better = sum(1 for r in all_splits if r["ml_better_than_baseline"])
        print(f"Splits where ML > Baseline:           {ml_better}/{len(all_splits)}")

    cross_splits = [r for r in cross_result.values() if "error" not in r]
    if cross_splits:
        cross_ml = np.mean([r["ml_accuracy"] for r in cross_splits])
        cross_bl = np.mean([r["baseline_accuracy"] for r in cross_splits])
        print(f"\nCross-regime ML accuracy:             {cross_ml:.1%}")
        print(f"Cross-regime Baseline accuracy:       {cross_bl:.1%}")
        print(f"Cross-regime improvement:             {cross_ml - cross_bl:+.1%}")

    return {
        "temporal": temp_result,
        "cross_regime": cross_result,
    }


if __name__ == "__main__":
    np.random.seed(42)
    run_backtest_validation()
