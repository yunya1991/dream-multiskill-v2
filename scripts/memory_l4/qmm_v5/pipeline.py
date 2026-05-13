"""V5 Pipeline: 端到端 QMM V5 原型入口。

整合: EventEncoder → VectorSpace → SignalGenerator → MemoryTrainer → TripleScreenAligner → Backtest

唯一入口: run_qmm_v5()
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .backtest import V5Backtester
from .encoder import EventEncoder
from .signal_generator import SignalGenerator
from .trainer import MemoryTrainer
from .triple_screen_aligner import TripleScreenAligner
from .types import GateResultV5, QMMEvent
from .vector_space import VectorSpace


def run_qmm_v5(
    cases: List[Dict[str, Any]],
    distills: List[Dict[str, Any]] = None,  # noqa: ARG001 — 预留
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """V5 端到端管道唯一入口。

    Returns:
        {
            "encoder": {"n_events": int},
            "vector_space": {"n_vectors": int, "n_clusters": int, ...},
            "signal": {"direction": str, "confidence": float, ...},
            "triple_screen": {"direction": str, "resonance_status": str, ...},
            "trainer": {"train_accuracy": float, "cv_accuracy_mean": float, ...},
            "backtest": GateResultV5 字段,
            "convergence": {"recommendation": str, "passed": bool},
        }
    """
    result = {}

    # === Step 1: EventEncoder ===
    encoder = EventEncoder()
    events = encoder.encode_batch(cases)
    result["encoder"] = {
        "n_events": len(events),
        "n_with_pnl": sum(1 for e in events if e.pnl_pct is not None),
        "regimes": _regime_distribution(events),
    }

    if not events:
        result["error"] = "NO_EVENTS_EXTRACTED"
        return result

    # === Step 2: VectorSpace ===
    vs = VectorSpace(random_state=42)
    vs.add_batch(events)

    n_clusters = min(5, len(events))
    cluster_result = vs.cluster(n_clusters=n_clusters)
    result["vector_space"] = {
        "n_vectors": len(vs.memory_vectors),
        "n_clusters": cluster_result["n_clusters"],
        "inertia": round(cluster_result["inertia"], 2),
        "cluster_sizes": _cluster_sizes(cluster_result["labels"]),
    }

    # === Step 3: SignalGenerator ===
    feature_matrix = encoder.to_numpy(events)
    sig_gen = SignalGenerator()
    signal = sig_gen.generate_signal(feature_matrix, events)
    result["signal"] = {
        "direction": signal["direction"],
        "confidence": signal["confidence"],
        "strength": signal["strength"],
    }

    # === Step 4: TripleScreenAligner ===
    ts_aligner = TripleScreenAligner()
    ts_result = ts_aligner.align(events)
    result["triple_screen"] = {
        "direction": ts_result["direction"],
        "score": ts_result["score"],
        "resonance_status": ts_result["resonance_status"],
    }

    # === Step 5: MemoryTrainer ===
    trainer = MemoryTrainer()
    X, y = trainer.prepare_data(feature_matrix, events)
    train_metrics = trainer.train(X, y)
    result["trainer"] = train_metrics

    # === Step 6: Walk-Forward Backtest ===
    backtester = V5Backtester(
        n_folds=config.get("n_folds", 5) if config else 5,
        min_train=config.get("min_train", 15) if config else 15,
        min_test=config.get("min_test", 5) if config else 5,
    )
    gate = backtester.run(feature_matrix, events)
    result["backtest"] = {
        "passed": gate.passed,
        "ml_accuracy": gate.ml_accuracy,
        "baseline_accuracy": gate.baseline_accuracy,
        "improvement": round(gate.ml_accuracy - gate.baseline_accuracy, 4),
        "train_test_gap": gate.train_test_gap,
        "fold_accuracies": gate.fold_accuracies,
        "overfitting": gate.overfitting,
        "reason_codes": gate.reason_codes,
    }
    result["convergence"] = {
        "recommendation": gate.recommendation(),
        "passed": gate.passed,
    }

    return result


def _regime_distribution(events: List[QMMEvent]) -> Dict[str, int]:
    """统计 regime 分布。"""
    dist: Dict[str, int] = {}
    for ev in events:
        dist[ev.regime] = dist.get(ev.regime, 0) + 1
    return dist


def _cluster_sizes(labels: Dict[str, int]) -> Dict[int, int]:
    """统计聚类大小。"""
    sizes: Dict[int, int] = {}
    for cid in labels.values():
        sizes[cid] = sizes.get(cid, 0) + 1
    return sizes
