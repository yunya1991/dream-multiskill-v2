# 系统进化工作流规范

定义反馈、审计、沙箱和回滚机制。

## 1. 工程部规范定位

本规范用于将“记忆驱动进化闭环”固化到约束层工作流规范中，作为进化工作流的工程实施基线。

权威设计文档：

- `docs/superpowers/specs/2026-05-11-memory-evolution-constraint-closed-loop-design.md`

P0 执行文档：

- `constraints/workflows-spec/evolution-p0-scope-freeze-2026-05-11.md`
- `constraints/workflows-spec/evolution-p0-contracts-v0.1.md`
- `constraints/workflows-spec/evolution-p0-state-machine-errors.md`
- `constraints/workflows-spec/evolution-p0-acceptance-checklist.md`
- `constraints/workflows-spec/evolution-p0-decision-gate-spec-v0.1.md`
- `constraints/workflows-spec/evolution-p0-rollback-pointer-spec-v0.1.md`

闭环主链：

- `memory -> evolution -> constraints`

强制约束：

- `constraints` 是唯一规则源（SSOT）。
- 约束升级唯一通道：`memory -> evolution -> constraints`。
- 任一验证关失败必须 fail-closed，不允许自动发布。

## 2. 最小闭环阶段

进化流程按最小闭环状态机执行：

1. `C0_COLLECTED`
2. `C1_AUDIT_PASSED`
3. `C2_SANDBOX_PASSED`
4. `C3_STRESS_PASSED`
5. `C4_SCENARIO_PASSED`
6. `C5_BACKTEST_PASSED`
7. `C6_APPROVED`
8. `C7_PROMOTED`
9. `C8_ROLLED_BACK`（仅发布后触发）

失败状态：

- `C_FAIL`：任一步失败，必须记录 `reason_code` 和 `evidence_refs`。

## 3. 自动化验证门禁

最小门禁集合：

- Audit Gate（字段完整性、证据链、冲突检测）
- Sandbox Gate（回放回归检查）
- Stress Gate（延迟/错误率/重试率）
- Scenario Gate（牛熊震荡极端情景）
- Backtest Gate（收益-风险与成本敏感性）

任一 Gate 失败：

- 阻断发布；
- 写审计报告；
- 触发人工复核流程。

## 4. GitHub 工程流程建议

建议工作流拆分：

- `memory-candidate-ingest.yml`
- `evolution-validation-gate.yml`
- `constraint-promotion.yml`
- `post-promotion-watch.yml`
- `constraint-rollback.yml`

建议 artifacts 目录：

- `artifacts/evolution/feedback/`
- `artifacts/evolution/audit/`
- `artifacts/evolution/sandbox/`
- `artifacts/evolution/stress/`
- `artifacts/evolution/scenario/`
- `artifacts/evolution/backtest/`
- `artifacts/evolution/promotion/`
- `artifacts/evolution/rollback/`

## 5. 分阶段实施路线（P0/P1/P2）

### P0（1~2 周，最小骨架）

- 固化候选与验证报告契约；
- 打通 `ingest -> audit -> sandbox -> decision`；
- 建立回滚指针；
- 产出可追溯审计 artifacts。

### P1（2~4 周，风控强化）

- 接入 stress/scenario/backtest；
- 固化风险阈值基线；
- 升级 required checks；
- 增加发布后观察窗与告警。

### P2（4~8 周，生产运营）

- 建立候选优先级评分；
- 增加版本对比指标看板（先 JSON）；
- 自动回滚执行器与 RTO 指标；
- 周/月审计报表与治理 KPI。

## 6. 同步记录

- `2026-05-11`：将“记忆驱动进化闭环（最小可行版）”正式纳入进化工作流工程部规范，并与 `constraints/workflows-spec/README.md` 建立索引同步。
- `2026-05-12`：补充 Day2 可执行规范：`Decision Gate` 判定规则与 `rollback pointer` 契约，作为脚本自动化落地基线。
