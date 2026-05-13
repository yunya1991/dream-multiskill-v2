"""V5 压力测试与场景测试。

验证修复数据泄露后的模型表现。
测试场景:
  1. 纯噪声数据 -> 准确率应 ~50%
  2. 真实 TradeCase 数据 -> 合理准确率 (50-75%)
  3. 小样本 (10 events) -> 应拒绝或低准确率
  4. 极端不平衡 (90% UP) -> 应检测不平衡
  5. 单一 regime -> 跨 regime 泛化测试
  6. 时间分布极端 (全部同一天) -> 时间衰减测试
  7. 缺失数据多 -> fail-closed 测试
"""

import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from .encoder import EventEncoder
from .pipeline import run_qmm_v5
from .signal_generator import SignalGenerator
from .trainer import MemoryTrainer
from .types import QMMEvent


# ============================================================
# 测试工具函数
# ============================================================

def _fake_case(
    pnl_pct: float,
    regime: str = "unknown",
    x: float = 0.0,
    y: float = 0.5,
    days_ago: int = 30,
    y_perf: float = 0.5,
    y_consistency: float = 0.5,
    y_human: float = 0.5,
    stages: List[str] = None,
    drawdown: float = 0.0,
) -> Dict[str, Any]:
    """构造假的 TradeCase。"""
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    if stages is None:
        stages = [{"stage": "A0"}, {"stage": "A5"}]
    return {
        "case_id": f"test_{random.randint(10000, 99999)}",
        "ts_start": ts,
        "quadrant": {
            "x": x,
            "y": y,
            "evidence": {
                "y_perf": y_perf,
                "y_consistency": y_consistency,
                "y_human": y_human,
            },
        },
        "environment_snapshot": {"regime": regime},
        "thinking_chain": stages,
        "decision_outcome": {
            "pnl_pct": pnl_pct,
            "pnl_usdt": (pnl_pct * 1000) if pnl_pct is not None else None,
            "drawdown": drawdown,
            "exit_reason": "test",
        },
    }


def _print_result(name: str, result: Dict[str, Any], passed: bool = True):
    status = "PASS" if passed else "FAIL"
    print(f"\n{'='*60}")
    print(f"[{status}] {name}")
    print(f"{'='*60}")
    for k, v in result.items():
        if k not in ("vector_space", "signal", "triple_screen", "backtest", "convergence", "encoder"):
            print(f"  {k}: {v}")
    if "backtest" in result:
        bt = result["backtest"]
        print(f"  backtest.passed: {bt.get('passed')}")
        print(f"  backtest.ml_accuracy: {bt.get('ml_accuracy')}")
        print(f"  backtest.baseline_accuracy: {bt.get('baseline_accuracy')}")
        print(f"  backtest.improvement: {bt.get('improvement')}")
        print(f"  backtest.overfitting: {bt.get('overfitting')}")
        print(f"  backtest.reason_codes: {bt.get('reason_codes')}")
    if "convergence" in result:
        c = result["convergence"]
        print(f"  convergence.recommendation: {c.get('recommendation')}")


# ============================================================
# 测试场景
# ============================================================

def test_noise_data():
    """测试 1: 纯噪声数据。

    特征与标签完全无关 -> ML 准确率应接近 50%（随机猜测）。
    如果远高于 55%，说明有 bug。
    """
    cases = []
    for _ in range(200):
        # 随机 pnl -> 标签随机
        pnl = random.uniform(-10, 10)
        # 特征与 pnl 无关
        cases.append(_fake_case(
            pnl_pct=pnl,
            x=random.uniform(-1, 1),
            y=random.uniform(0, 1),
            y_perf=random.uniform(0, 1),
            y_consistency=random.uniform(0, 1),
            y_human=random.uniform(0, 1),
            regime=random.choice(["bull", "bear", "oscillation"]),
            days_ago=random.randint(1, 180),
        ))

    result = run_qmm_v5(cases, config={"n_folds": 5, "min_train": 15, "min_test": 10})
    ml_acc = result.get("backtest", {}).get("ml_accuracy", 0)
    passed = ml_acc < 0.60  # 不应超过 60%（允许一点随机波动）
    _print_result(
        f"Noise Data: ML accuracy should be ~50%, got {ml_acc:.4f}",
        result, passed,
    )
    return passed


def test_realistic_data():
    """测试 2: 模拟真实 TradeCase 数据。

    使用与真实数据分布相似的参数。
    """
    cases = []
    regimes = ["bull", "bear", "oscillation", "crash", "recovery", "consolidation"]
    regime_weights = [0.28, 0.15, 0.15, 0.15, 0.14, 0.13]

    for _ in range(200):
        regime = random.choices(regimes, weights=regime_weights, k=1)[0]
        # 不同 regime 有不同的 pnl 分布
        if regime == "bull":
            pnl = random.gauss(2.0, 4.0)
            x = random.gauss(0.3, 0.3)
        elif regime == "bear":
            pnl = random.gauss(-1.5, 4.0)
            x = random.gauss(-0.3, 0.3)
        else:
            pnl = random.gauss(0.0, 3.0)
            x = random.gauss(0.0, 0.3)

        cases.append(_fake_case(
            pnl_pct=round(pnl, 2),
            regime=regime,
            x=round(np.clip(x, -1, 1), 4),
            y=round(np.clip(random.gauss(0.5, 0.2), 0, 1), 4),
            y_perf=round(np.clip(random.gauss(0.6, 0.15), 0, 1), 4),
            y_consistency=round(np.clip(random.gauss(0.5, 0.2), 0, 1), 4),
            y_human=round(np.clip(random.gauss(0.5, 0.2), 0, 1), 4),
            drawdown=round(abs(random.gauss(0, 2)), 2),
            days_ago=random.randint(1, 365),
        ))

    result = run_qmm_v5(cases, config={"n_folds": 5, "min_train": 15, "min_test": 10})
    ml_acc = result.get("backtest", {}).get("ml_accuracy", 0)
    # 合理范围: 50-75%
    passed = 0.45 <= ml_acc <= 0.80
    _print_result(
        f"Realistic Data: ML accuracy should be 45-80%, got {ml_acc:.4f}",
        result, passed,
    )
    return passed


def test_small_sample():
    """测试 3: 小样本 (10 events)。

    数据不足以训练 -> 应拒绝或给低准确率。
    """
    cases = []
    for _ in range(10):
        cases.append(_fake_case(
            pnl_pct=random.uniform(-5, 5),
            x=random.uniform(-1, 1),
            y=random.uniform(0, 1),
            days_ago=random.randint(1, 90),
        ))

    result = run_qmm_v5(cases, config={"n_folds": 3, "min_train": 15, "min_test": 5})
    ml_acc = result.get("backtest", {}).get("ml_accuracy", 0)
    passed_result = result.get("backtest", {}).get("passed", False) is False
    _print_result(
        f"Small Sample: should NOT pass, passed={passed_result}, ml_acc={ml_acc:.4f}",
        result, passed_result,
    )
    return passed_result


def test_imbalanced_classes():
    """测试 4: 极端类别不平衡 (90% UP)。

    模型可能退化为预测多数类。
    """
    cases = []
    # 90% UP
    for _ in range(90):
        cases.append(_fake_case(
            pnl_pct=random.uniform(0.1, 10),
            x=random.uniform(0, 1),
            regime="bull",
            days_ago=random.randint(1, 180),
        ))
    # 10% DOWN
    for _ in range(10):
        cases.append(_fake_case(
            pnl_pct=random.uniform(-10, -0.1),
            x=random.uniform(-1, 0),
            regime="bear",
            days_ago=random.randint(1, 180),
        ))

    result = run_qmm_v5(cases, config={"n_folds": 5, "min_train": 15, "min_test": 10})
    ml_acc = result.get("backtest", {}).get("ml_accuracy", 0)
    bl_acc = result.get("backtest", {}).get("baseline_accuracy", 0)
    # ML 不应显著优于基线（因为多数类就是答案）
    improvement = ml_acc - bl_acc
    passed = improvement < 0.15  # ML 提升不应超过 15%
    _print_result(
        f"Imbalanced (90% UP): improvement={improvement:.4f}, ml={ml_acc:.4f}, bl={bl_acc:.4f}",
        result, passed,
    )
    return passed


def test_single_regime():
    """测试 5: 单一 regime (全部 bull)。

    检查模型是否能处理单一市场状态。
    """
    cases = []
    for _ in range(100):
        pnl = random.gauss(2.0, 5.0)
        cases.append(_fake_case(
            pnl_pct=round(pnl, 2),
            regime="bull",
            x=round(random.uniform(-0.5, 1), 4),
            y=round(random.uniform(0.2, 0.9), 4),
            days_ago=random.randint(1, 180),
        ))

    result = run_qmm_v5(cases, config={"n_folds": 5, "min_train": 15, "min_test": 10})
    ml_acc = result.get("backtest", {}).get("ml_accuracy", 0)
    passed = 0.40 <= ml_acc <= 0.85
    _print_result(
        f"Single Regime (bull): ML accuracy should be 40-85%, got {ml_acc:.4f}",
        result, passed,
    )
    return passed


def test_time_concentration():
    """测试 6: 时间分布极端 (全部同一天)。

    时间衰减权重相同 -> 应正常工作。
    """
    cases = []
    for _ in range(100):
        pnl = random.gauss(0, 4)
        cases.append(_fake_case(
            pnl_pct=round(pnl, 2),
            x=round(random.uniform(-1, 1), 4),
            y=round(random.uniform(0, 1), 4),
            days_ago=0,  # 全部同一天
        ))

    result = run_qmm_v5(cases, config={"n_folds": 5, "min_train": 15, "min_test": 10})
    ml_acc = result.get("backtest", {}).get("ml_accuracy", 0)
    passed = 0.40 <= ml_acc <= 0.80
    _print_result(
        f"Time Concentration: ML accuracy should be 40-80%, got {ml_acc:.4f}",
        result, passed,
    )
    return passed


def test_missing_data():
    """测试 7: 大量缺失 pnl 数据。

    >50% 无 pnl -> 数据不足，应 fail。
    """
    cases = []
    for _ in range(100):
        pnl = None if random.random() < 0.7 else random.uniform(-5, 5)
        cases.append(_fake_case(
            pnl_pct=pnl,
            x=round(random.uniform(-1, 1), 4),
            y=round(random.uniform(0, 1), 4),
            days_ago=random.randint(1, 180),
        ))

    result = run_qmm_v5(cases, config={"n_folds": 5, "min_train": 15, "min_test": 10})
    passed_result = result.get("backtest", {}).get("passed", False) is False
    _print_result(
        f"Missing Data (70% no pnl): should NOT pass, passed={passed_result}",
        result, passed_result,
    )
    return passed_result


def test_crash_regime():
    """测试 8: Crash regime 集中测试。

    极端下跌行情 -> 模型应能区分。
    """
    cases = []
    for _ in range(80):
        pnl = random.gauss(-5, 3)
        cases.append(_fake_case(
            pnl_pct=round(pnl, 2),
            regime="crash",
            x=round(random.uniform(-1, -0.2), 4),
            y=round(random.uniform(0.5, 1), 4),
            drawdown=round(random.uniform(5, 30), 2),
            days_ago=random.randint(1, 180),
        ))
    # 少量其他 regime 作为对比
    for _ in range(40):
        pnl = random.gauss(1, 3)
        cases.append(_fake_case(
            pnl_pct=round(pnl, 2),
            regime=random.choice(["bull", "recovery"]),
            x=round(random.uniform(-0.3, 0.8), 4),
            days_ago=random.randint(1, 180),
        ))

    result = run_qmm_v5(cases, config={"n_folds": 5, "min_train": 15, "min_test": 10})
    ml_acc = result.get("backtest", {}).get("ml_accuracy", 0)
    passed = 0.45 <= ml_acc <= 0.85
    _print_result(
        f"Crash Regime: ML accuracy should be 45-85%, got {ml_acc:.4f}",
        result, passed,
    )
    return passed


def test_leakage_detection():
    """测试 9: 数据泄露检测（对照实验）。

    故意用含 pnl_pct 的特征向量训练，验证准确率会异常高。
    证明修复是有效的。
    """
    encoder = EventEncoder()
    cases = []
    for _ in range(150):
        pnl = random.gauss(0, 4)
        cases.append(_fake_case(
            pnl_pct=round(pnl, 2),
            x=round(random.uniform(-1, 1), 4),
            y=round(random.uniform(0, 1), 4),
            days_ago=random.randint(1, 180),
        ))

    events = encoder.encode_batch(cases)
    feature_matrix = encoder.to_numpy(events)

    # 正常特征 (12 维)
    trainer_clean = MemoryTrainer()
    X_clean, y_clean = trainer_clean.prepare_data(feature_matrix, events)
    metrics_clean = trainer_clean.train(X_clean, y_clean)

    # 泄露特征: 手动添加 pnl_pct 和 direction 作为额外特征
    leaked_vectors = []
    for ev in events:
        v = ev.to_feature_vector()
        v.append(ev.pnl_pct or 0.0)  # 泄露特征 1
        direction = 1.0 if ev.is_profit else (-1.0 if ev.pnl_pct is not None and ev.pnl_pct < 0 else 0.0)
        v.append(direction)  # 泄露特征 2
        leaked_vectors.append(v)
    X_leaked = np.array(leaked_vectors, dtype=np.float64)

    trainer_leaked = MemoryTrainer()
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_leaked_scaled = scaler.fit_transform(X_leaked)
    metrics_leaked = trainer_leaked.train(X_leaked_scaled, y_clean)

    clean_acc = metrics_clean.get("cv_accuracy_mean", 0)
    leaked_acc = metrics_leaked.get("cv_accuracy_mean", 0)

    passed = leaked_acc > clean_acc + 0.10  # 泄露版本应明显更好
    _print_result(
        f"Leakage Detection: clean={clean_acc:.4f}, leaked={leaked_acc:.4f}, "
        f"diff={leaked_acc - clean_acc:.4f}",
        {"clean_accuracy": clean_acc, "leaked_accuracy": leaked_acc},
        passed,
    )
    return passed


def test_extreme_drawdowns():
    """测试 10: 极端 drawdown 事件。

    大 drawdown 可能与亏损相关。
    """
    cases = []
    # 高 drawdown -> 倾向亏损
    for _ in range(50):
        pnl = random.gauss(-3, 2)
        cases.append(_fake_case(
            pnl_pct=round(pnl, 2),
            drawdown=round(random.uniform(10, 40), 2),
            x=round(random.uniform(-1, -0.2), 4),
            days_ago=random.randint(1, 180),
        ))
    # 低 drawdown -> 倾向盈利
    for _ in range(50):
        pnl = random.gauss(2, 2)
        cases.append(_fake_case(
            pnl_pct=round(pnl, 2),
            drawdown=round(random.uniform(0, 3), 2),
            x=round(random.uniform(0, 0.8), 4),
            days_ago=random.randint(1, 180),
        ))

    result = run_qmm_v5(cases, config={"n_folds": 5, "min_train": 15, "min_test": 10})
    ml_acc = result.get("backtest", {}).get("ml_accuracy", 0)
    # drawdown 与 pnl 有相关性，但不完美 -> 准确率中等
    passed = 0.50 <= ml_acc <= 0.85
    _print_result(
        f"Extreme Drawdowns: ML accuracy should be 50-85%, got {ml_acc:.4f}",
        result, passed,
    )
    return passed


def test_oscillation_regime():
    """测试 11: Oscillation regime (震荡行情)。

    pnl 接近 0，方向随机 -> 最难预测的行情。
    """
    cases = []
    for _ in range(150):
        pnl = random.gauss(0, 1.5)  # 窄分布，接近 0
        cases.append(_fake_case(
            pnl_pct=round(pnl, 2),
            regime="oscillation",
            x=round(random.uniform(-0.3, 0.3), 4),  # x 接近 0
            y=round(random.uniform(0.3, 0.7), 4),
            days_ago=random.randint(1, 180),
        ))

    result = run_qmm_v5(cases, config={"n_folds": 5, "min_train": 15, "min_test": 10})
    ml_acc = result.get("backtest", {}).get("ml_accuracy", 0)
    # 震荡行情应接近随机猜测
    passed = ml_acc < 0.65
    _print_result(
        f"Oscillation: ML accuracy should be <65%, got {ml_acc:.4f}",
        result, passed,
    )
    return passed


def test_signal_generator_robustness():
    """测试 12: SignalGenerator 鲁棒性。

    不同事件组合下信号是否合理。
    """
    encoder = EventEncoder()
    sig_gen = SignalGenerator()
    all_passed = True

    # 场景 A: 全部 UP
    up_events = []
    for _ in range(30):
        ev = encoder.encode(_fake_case(pnl_pct=random.uniform(1, 10), x=0.5, regime="bull"))
        if ev:
            up_events.append(ev)
    if up_events:
        feat = encoder.to_numpy(up_events)
        sig = sig_gen.generate_signal(feat, up_events)
        if sig["direction"] != "UP":
            print(f"  Signal A (all UP): expected UP, got {sig['direction']}")
            all_passed = False

    # 场景 B: 全部 DOWN
    down_events = []
    for _ in range(30):
        ev = encoder.encode(_fake_case(pnl_pct=random.uniform(-10, -1), x=-0.5, regime="bear"))
        if ev:
            down_events.append(ev)
    if down_events:
        feat = encoder.to_numpy(down_events)
        sig = sig_gen.generate_signal(feat, down_events)
        if sig["direction"] != "DOWN":
            print(f"  Signal B (all DOWN): expected DOWN, got {sig['direction']}")
            all_passed = False

    # 场景 C: 混合
    mixed_events = []
    for _ in range(15):
        ev = encoder.encode(_fake_case(pnl_pct=random.uniform(-1, 1), x=0, regime="oscillation"))
        if ev:
            mixed_events.append(ev)
    if mixed_events:
        feat = encoder.to_numpy(mixed_events)
        sig = sig_gen.generate_signal(feat, mixed_events)
        if sig["confidence"] > 0.5:
            print(f"  Signal C (mixed): expected low confidence, got {sig['confidence']}")
            all_passed = False

    _print_result(
        f"Signal Generator Robustness: {'all passed' if all_passed else 'some failed'}",
        {}, all_passed,
    )
    return all_passed


# ============================================================
# 主入口
# ============================================================

def run_all_stress_tests():
    """运行所有压力测试。"""
    print("=" * 60)
    print("QMM V5 Stress Tests & Scenario Tests")
    print("=" * 60)

    tests = [
        ("1. Noise Data", test_noise_data),
        ("2. Realistic Data", test_realistic_data),
        ("3. Small Sample", test_small_sample),
        ("4. Imbalanced Classes", test_imbalanced_classes),
        ("5. Single Regime", test_single_regime),
        ("6. Time Concentration", test_time_concentration),
        ("7. Missing Data", test_missing_data),
        ("8. Crash Regime", test_crash_regime),
        ("9. Leakage Detection", test_leakage_detection),
        ("10. Extreme Drawdowns", test_extreme_drawdowns),
        ("11. Oscillation Regime", test_oscillation_regime),
        ("12. Signal Generator", test_signal_generator_robustness),
    ]

    results = []
    for name, fn in tests:
        try:
            passed = fn()
            results.append((name, passed))
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 汇总
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed_count = sum(1 for _, p in results if p)
    total = len(results)
    for name, passed in results:
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name}")
    print(f"\n  Total: {passed_count}/{total} passed")

    return passed_count == total


if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)
    success = run_all_stress_tests()
    exit(0 if success else 1)
