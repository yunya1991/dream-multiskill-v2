"""蒸馏引擎模块 — 11步流程 + 三问逻辑。

从 ReviewRecord 出发，完成完整的蒸馏流程：
意图→调研→理论→假设→测试→结论→落地→监控→复盘→做梦→更新

回答三个核心问题：
- 是什么？(what_is_it)
- 为什么？(why_it_works)
- 怎么做？(how_to_apply)

v0.2 新增模块 — Phase 3 (P2)
"""

import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.memory_l4.paths import memory_l4_distills_dir, memory_l4_cases_dir


def now_iso_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ── 蒸馏流程定义 ──

DISTILL_STEPS = [
    "intent",       # 意图: 明确问题
    "investigation", # 调研: 现状调查与矛盾分析
    "theory",        # 理论: 调用知识库、历史事件、联网搜索
    "hypothesis",    # 假设: 基于矛盾分析、现状、理论
    "test",          # 测试与观测: 验证假设，搜集数据
    "conclusion",    # 结论: 根据假设与实际表现推导
    "implementation",# 落地: 实施方案
    "monitoring",    # 监控: 监控结果
    "review",        # 复盘: 理论与实践一致性检验
    "reflection",    # 做梦: 外部反思
    "optimization",  # 更新优化: 最终优化方案
]


def init_distill(
    review_record: Dict[str, Any],
    kind: str = "risk_signal",
    distill_id: Optional[str] = None,
) -> Dict[str, Any]:
    """从 ReviewRecord 初始化蒸馏记录。

    Args:
        review_record: ReviewRecord 数据
        kind: 蒸馏类型
        distill_id: 蒸馏标识，默认自动生成

    Returns:
        初始 Distill 字典
    """
    did = distill_id or f"D_{now_iso_local()[:19].replace(':', '').replace('-', '')}"

    case_id = review_record.get("case_id", "")
    claim_draft = _draft_claim_from_review(review_record)

    return {
        "distill_id": did,
        "version": "v0.2",
        "kind": kind,
        "what_is_it": {
            "claim": claim_draft,
            "definition": None,
            "classification": [kind],
        },
        "why_it_works": {
            "causal_analysis": "",
            "theory_basis": [],
            "evidence_chain": [],
            "contradiction_resolved": None,
        },
        "how_to_apply": {
            "actionable_rules": [],
            "trigger_conditions": [],
            "step_by_step": [],
            "risk_warnings": [],
        },
        "supporting_case_ids": [case_id] if case_id else [],
        "claim": claim_draft,
        "actionable_rules": [],
        "process_trace": {
            "intent": None,
            "investigation": None,
            "theory_refs": [],
            "hypothesis": None,
            "test_results": None,
            "conclusion": None,
            "implementation": None,
            "monitoring": None,
            "review_result": None,
            "reflection": None,
            "optimization": None,
        },
        "quadrant": {
            "x": 0.0,
            "y": 0.0,
            "evidence": {
                "weights": {"perf": 0.4, "consistency": 0.4, "human": 0.2},
                "y_perf": 0.0,
                "y_consistency": 0.0,
                "y_human": 0.0,
                "notes": "Auto-generated from distill_engine v0.2",
            },
        },
        "migration_history": [],
    }


def _draft_claim_from_review(review: Dict[str, Any]) -> str:
    """从 ReviewRecord 自动生成初始 claim。"""
    direction = review.get("direction", "mixed")
    case_id = review.get("case_id", "unknown")
    mistakes = review.get("mistakes") or []
    successes = review.get("successes") or []

    if direction == "failure" and mistakes:
        top_mistake = mistakes[0].get("what", "unknown issue")
        return f"Failure pattern in {case_id}: {top_mistake}"
    elif direction == "success" and successes:
        top_success = successes[0].get("what", "unknown benefit")
        return f"Success pattern in {case_id}: {top_success}"
    else:
        return f"Mixed outcome pattern in {case_id}"


# ── 11 步蒸馏流程 ──

def step_intent(distill: Dict[str, Any], review_record: Dict[str, Any]) -> Dict[str, Any]:
    """Step 1: 意图 — 明确问题。"""
    pt = distill["process_trace"]
    direction = review_record.get("direction", "unknown")
    case_id = review_record.get("case_id", "")

    problem = f"[{direction.upper()}] TradeCase {case_id}"
    if direction == "failure":
        mistakes = review_record.get("mistakes") or []
        if mistakes:
            problem += f" — core issue: {mistakes[0].get('what', 'unknown')}"
    elif direction == "success":
        successes = review_record.get("successes") or []
        if successes:
            problem += f" — key success: {successes[0].get('what', 'unknown')}"

    pt["intent"] = problem
    return distill


def step_investigation(distill: Dict[str, Any]) -> Dict[str, Any]:
    """Step 2: 调研 — 现状调查与矛盾分析。"""
    pt = distill["process_trace"]
    # TODO: 从 memory index 中检索类似案例，分析矛盾
    pt["investigation"] = "Pending: cross-reference similar cases and contradiction patterns"
    return distill


def step_theory(distill: Dict[str, Any], knowledge_refs: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Step 3: 理论 — 调用知识库、历史事件、联网搜索。"""
    pt = distill["process_trace"]
    pt["theory_refs"] = knowledge_refs or []
    # TODO: 联网搜索相关策略和理论
    return distill


def step_hypothesis(distill: Dict[str, Any]) -> Dict[str, Any]:
    """Step 4: 假设 — 基于矛盾分析、现状、理论生成假设。"""
    pt = distill["process_trace"]
    claim = distill.get("claim", "")
    pt["hypothesis"] = f"Based on [{claim}], the proposed hypothesis is pending analysis"
    return distill


def step_test(distill: Dict[str, Any]) -> Dict[str, Any]:
    """Step 5: 测试与观测 — 验证假设，搜集数据。"""
    pt = distill["process_trace"]
    # TODO: 根据假设设计测试场景，搜集数据
    pt["test_results"] = "Pending: backtest or live observation data"
    return distill


def step_conclusion(distill: Dict[str, Any]) -> Dict[str, Any]:
    """Step 6: 结论 — 根据假设与实际表现推导正确结果。"""
    pt = distill["process_trace"]
    pt["conclusion"] = "Pending: synthesize test results into actionable conclusion"
    return distill


def step_implementation(distill: Dict[str, Any]) -> Dict[str, Any]:
    """Step 7: 落地 — 实施方案。"""
    pt = distill["process_trace"]
    pt["implementation"] = "Pending: define implementation steps and constraints"
    return distill


def step_monitoring(distill: Dict[str, Any]) -> Dict[str, Any]:
    """Step 8: 监控 — 监控结果。"""
    pt = distill["process_trace"]
    pt["monitoring"] = "Pending: define monitoring metrics and alerting"
    return distill


def step_review(distill: Dict[str, Any]) -> Dict[str, Any]:
    """Step 9: 复盘 — 理论与实践一致性检验。"""
    pt = distill["process_trace"]
    pt["review_result"] = "Pending: verify theory-practice consistency"
    return distill


def step_reflection(distill: Dict[str, Any]) -> Dict[str, Any]:
    """Step 10: 做梦 — 外部反思。"""
    pt = distill["process_trace"]
    pt["reflection"] = "Pending: external perspective reflection"
    return distill


def step_optimization(distill: Dict[str, Any]) -> Dict[str, Any]:
    """Step 11: 更新优化 — 最终优化方案。"""
    pt = distill["process_trace"]
    pt["optimization"] = "Pending: finalize optimization plan"
    return distill


# ── 三问逻辑 ──

def answer_what_is_it(distill: Dict[str, Any]) -> Dict[str, Any]:
    """回答"是什么" — 填充 what_is_it 层。"""
    d = dict(distill)
    wi = d.get("what_is_it") or {}
    wi["claim"] = d.get("claim", "")
    # TODO: 基于 process_trace 的 intent + investigation 生成 definition
    wi["definition"] = "Pending: derive definition from process trace"
    d["what_is_it"] = wi
    return d


def answer_why_it_works(distill: Dict[str, Any]) -> Dict[str, Any]:
    """回答"为什么" — 填充 why_it_works 层。"""
    d = dict(distill)
    ww = d.get("why_it_works") or {}
    ww["causal_analysis"] = "Pending: derive from hypothesis + conclusion"
    d["why_it_works"] = ww
    return d


def answer_how_to_apply(distill: Dict[str, Any]) -> Dict[str, Any]:
    """回答"怎么做" — 填充 how_to_apply 层。"""
    d = dict(distill)
    ha = d.get("how_to_apply") or {}
    ha["actionable_rules"] = d.get("actionable_rules", [])
    d["how_to_apply"] = ha
    return d


def complete_distill(distill: Dict[str, Any]) -> Dict[str, Any]:
    """完成蒸馏 — 计算象限坐标。"""
    d = dict(distill)
    # 触发三问
    d = answer_what_is_it(d)
    d = answer_why_it_works(d)
    d = answer_how_to_apply(d)
    return d


def save_distill(distill: Dict[str, Any], out_path: Optional[Path] = None) -> Path:
    """保存蒸馏记录到文件。"""
    did = distill.get("distill_id", "unknown")
    target = out_path or (memory_l4_distills_dir() / f"{did}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(distill, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
