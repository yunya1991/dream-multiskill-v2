# 通信契约 v0.1

## 1. 目标与范围

本契约用于规范三大初期迁移对象之间的通信与调用关系：

- 底层约束层：`constraints/`
- 记忆工作流：`workflows/memory/`
- 交易决策工作流：`workflows/trading-decision/`

并明确记忆经验沉淀为底层约束时，必须经过系统进化工作流：`workflows/evolution/`。

## 2. 架构关系（强约束）

```text
constraints  --约束-->  memory / trading-decision / evolution
trading-decision --读写--> memory
memory --候选提交--> evolution
evolution --审核发布--> constraints
```

强制规则：

- `constraints` 是唯一规则源（SSOT）。
- `memory` 不能直接改写 `constraints`。
- `trading-decision` 不能绕过约束校验执行关键动作。
- 约束升级唯一通道：`memory -> evolution -> constraints`。

## 3. 通信模式

### 3.1 同步调用（主链）

用于 A0-A9 阶段内的关键决策路径：

1. 交易阶段开始前读取约束。
2. 调用记忆检索获取历史经验。
3. 执行阶段逻辑并产出结果。
4. 阶段结束前执行约束校验并落产物。

### 3.2 异步调用（后处理）

用于非阻塞沉淀流程：

- 阶段产物回写 episode/case/distill。
- 统计聚合与索引更新。
- 约束候选生成与提交至 evolution。

## 4. 逻辑接口契约

以下为逻辑接口，不绑定具体语言实现。

### 4.1 约束层接口

- `resolve_constraint(workflow, stage) -> {constraint_version, rules}`
- `validate_payload(workflow, stage, payload) -> {pass, violations[]}`

### 4.2 记忆层接口

- `query_memory(context) -> {cases[], patterns[], risk_signals[]}`
- `write_episode(trace) -> {episode_id, stored_level}`
- `emit_constraint_candidate(memory_item_id) -> {candidate_id}`

### 4.3 交易决策接口

- `run_stage(stage_id, input) -> {output, evidence_refs[]}`
- `finalize_trace(trace_id) -> {summary, artifact_refs[]}`

### 4.4 系统进化接口

- `ingest_candidate(candidate) -> {accepted, queue_id}`
- `evaluate_candidate(queue_id) -> {decision, reasons[]}`
- `promote_constraint(queue_id) -> {new_constraint_version}`
- `rollback_constraint(version) -> {rolled_back_to}`

## 5. 统一字段契约（必填）

所有主链产物与关键事件必须包含：

- `trace_id`：一次完整链路唯一 ID
- `stage_id`：A0-A9 或 memory 子阶段
- `constraint_version`：执行时使用的约束版本
- `memory_refs[]`：引用的记忆实体 ID
- `evidence_refs[]`：证据文件路径或证据 ID
- `timestamp`：UTC 时间戳
- `producer`：产物来源工作流
- `schema_version`：当前数据契约版本

## 6. 产物落地约定

- `artifacts/trading/`：A0-A9 阶段产物与总决策摘要
- `artifacts/memory/`：episode、distill、index、stats
- `artifacts/evolution/`：候选评估、沙箱报告、发布记录、回滚记录

禁止落地“不可追溯产物”：无 `trace_id` 或无 `evidence_refs` 的文件不得进入主链目录。

## 7. 约束升级闭环契约

### 7.1 候选来源

- 来源仅允许为已沉淀的记忆经验（episode/case/distill）。
- 每条候选必须标明来源证据链。

### 7.2 审批流程

1. `memory` 提交 `constraint_candidate` 到 `evolution/feedback`。
2. `evolution/audit` 执行一致性、冲突、风险评估。
3. `evolution/sandbox` 执行回放与压力验证。
4. 通过后由 `evolution` 发布新约束版本到 `constraints`。
5. 发布后进入持续监控，异常触发 `evolution/rollback`。

### 7.3 发布门禁

必须同时满足：

- 冲突检测通过
- 沙箱回放通过
- 风险阈值未超限
- 可回滚目标已准备

## 8. 错误语义与处置

- `CONSTRAINT_VALIDATION_FAILED`：约束校验失败，主链中止（fail-closed）。
- `MEMORY_REFERENCE_MISSING`：关键记忆引用缺失，转人工审计或降级执行。
- `EVIDENCE_INCOMPLETE`：证据链不完整，不允许提交候选或发布约束。
- `SANDBOX_REGRESSION`：沙箱回归失败，拒绝升级并记录原因。

## 9. 可观测性与审计要求

- 每次关键调用都要有审计记录（输入摘要、输出摘要、耗时、结果）。
- 每次约束发布都要有版本变更记录与回滚指针。
- 支持按 `trace_id` 完整回放链路。

## 10. 版本治理

- 当前版本：`v0.1`
- 适用阶段：架构基线与初期迁移阶段
- 变更策略：新增字段向后兼容；删除字段需先升 `schema_version`
- 权威维护位置：`constraints/workflows-spec/`

## 11. 实施优先级（仅文档层）

1. 先对齐字段契约与错误语义。
2. 再对齐 A0-A9 与 memory 的同步/异步边界。
3. 最后固化 `memory -> evolution -> constraints` 发布门禁。

## 12. 同步记录

- `2026-05-10T16:02:59Z`：同步迁移 `dream-trading-automation` 最新记忆 L4 到 `dream-multiskill-v2`，覆盖 `scripts/memory_l4/`、`workflows/memory/memory_engine/`、`.workbuddy/memory_l4/schemas/` 及对应测试集合。
