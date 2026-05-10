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

## 约束

- 入口层保持薄封装，不承载复杂业务逻辑。
- 阶段产物写入统一 `artifacts/trading/`，并携带 `trace_id`。
- 后续 A3-A9 迁移需沿用同一入口模式与契约字段。
