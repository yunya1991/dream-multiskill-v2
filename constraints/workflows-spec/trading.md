# 交易决策工作流规范

定义 A0-A9 链路的阶段职责、准入门禁和产物契约。

## A0-A2 显式入口映射（第一批迁移）

- `workflows/trading-decision/A0_contradiction/entrypoint.py`
  - `run_a0_contradiction_analysis`：矛盾排序、主矛盾识别、方向输出
- `workflows/trading-decision/A1_research/entrypoint.py`
  - `run_a1_research`：调研结果结构化并写入 A1 产物
- `workflows/trading-decision/A2_first-principles/entrypoint.py`
  - `run_a2_first_principles`：第一性原理核心指标计算与 A2 产物输出

## 第一批技能迁移清单（A0-A2）

- `skills/1-TRADE/dream-contradiction-theory/SKILL.md`
- `skills/1-TRADE/dream-strategy-research/SKILL.md`
- `skills/1-TRADE/dream-first-principles/SKILL.md`

## A3-A5 显式入口映射（第二批迁移）

- `workflows/trading-decision/A3_simulation/entrypoint.py`
  - `run_a3_simulation`：评分与波动驱动策略模式选择
- `workflows/trading-decision/A4_validation/entrypoint.py`
  - `run_a4_validation`：风控门禁判定（PASS/REVIEW/BLOCK）
- `workflows/trading-decision/A5_execution/entrypoint.py`
  - `run_a5_execution`：生成最小下单计划

## 第二批技能迁移清单（A3-A5）

- `skills/1-TRADE/dream-strategy-designer/SKILL.md`
- `skills/1-TRADE/dream-strategy-parser/SKILL.md`
- `skills/1-TRADE/dream-tactical-validator/SKILL.md`
- `skills/1-TRADE/dream-pretrade-gatekeeper/SKILL.md`
- `skills/1-TRADE/dream-tactical-executor/SKILL.md`

## A6-A9 显式入口映射（第三批迁移）

- `workflows/trading-decision/A6_intelligence/entrypoint.py`
  - `run_a6_intelligence`：告警和信号漂移摘要输出
- `workflows/trading-decision/A7_audit/entrypoint.py`
  - `run_a7_audit`：审计检查与状态输出
- `workflows/trading-decision/A8_theory-practice/entrypoint.py`
  - `run_a8_theory_practice`：理论-实践偏差评估
- `workflows/trading-decision/A9_exit/entrypoint.py`
  - `run_a9_exit`：离场动作建议输出

## 第三批技能迁移清单（A6-A9）

- `skills/1-TRADE/dream-intelligence-monitor/SKILL.md`
- `skills/1-TRADE/dream-signal-scoring-spec/SKILL.md`
- `skills/1-TRADE/dream-regime-detector/SKILL.md`
- `skills/1-TRADE/A7-practice-theory/SKILL.md`
- `skills/1-TRADE/A8-theory-practice-verification/SKILL.md`
- `skills/1-TRADE/dream-exit-skill-v2/SKILL.md`

## 约束

- 入口层保持薄封装，不承载复杂业务逻辑。
- 阶段产物写入统一 `artifacts/trading/`，并携带 `trace_id`。
- 后续 A3-A9 迁移需沿用同一入口模式与契约字段。
