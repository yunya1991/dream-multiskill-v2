# L4记忆工程架构规范（约束层）

Date: 2026-05-12  
Status: Active Baseline (Constraint Layer)  
Type: 顶层工程设计在约束层的正式落地镜像  
Upstream Canonical: `docs/superpowers/specs/2026-05-12-l4-memory-architecture-and-workflow-design.md`

## 1. 规范定位

本文件是 L4 记忆工作流在约束层的核心工程规范。目标是把顶层设计固化为可执行条款，并作为后续分支实现对齐基准。

主从关系：

- 顶层设计（主）：`docs/superpowers/specs/2026-05-12-l4-memory-architecture-and-workflow-design.md`
- 约束镜像（从）：`constraints/workflows-spec/l4-memory/architecture-and-workflow-design.md`

## 2. 强制约束

- `constraints` 是唯一规则源（SSOT）。
- 进化主链必须为：`memory -> evolution -> constraints`。
- 任一阶段失败必须 fail-closed，并落审计字段：`stage/reason_code/evidence_refs`。
- 入口层只做薄封装，复杂逻辑下沉至 `memory_engine` 与 `scripts/memory_l4/`。

## 3. 核心对象契约（最小集）

### 3.1 TradeCase.vNext

- `thinking_chain[]`
- `evidence_chain[]`
- `decision_outcome`

兼容策略：保留旧字段（如 `plan.steps`）读取，新字段先可选后强约束。

### 3.2 ReviewRecord

- `mistakes[]`
- `successes[]`
- `theory_practice_gap`

### 3.3 DistillRecord.vNext

- `what_is_it`
- `why_it_works`
- `how_to_apply`
- `process_trace`

兼容策略：保留 `claim/actionable_rules` 并建立映射。

### 3.4 StatsSnapshot

四象限 `x/y` 不变，新增过滤维度：

- `regime`
- `category`
- `severity`

## 4. L4状态机与失败语义

状态机：

- `M0_CASE_REGISTERED`
- `M1_REVIEW_COMPLETED`
- `M2_DISTILL_COMPLETED`
- `M3_STATS_UPDATED`
- `M4_CANDIDATE_EMITTED`
- `M_FAIL`

失败语义最小集：

- `CASE_INCOMPLETE`
- `EVIDENCE_MISSING`
- `REVIEW_INCONSISTENT`
- `DISTILL_INVALID`
- `STATS_INTEGRITY_FAILED`
- `CANDIDATE_EMIT_BLOCKED`

## 5. 顶层到实现映射

- 入口层：`workflows/memory/L1~L4_archive/entrypoint.py`
- 编排层：`workflows/memory/memory_engine/`
- L4 脚本：`scripts/memory_l4/`

目标能力（允许分阶段落地）：

- `review_engine`
- `a7_a8_adapter`
- `thinking_chain_index_extension`

## 6. 阶段路线

- P0：契约固化
- P1：链路打通
- P2：演化强化
- P3：认知强化

## 7. 维护规则

- 任何字段/状态机变更必须同步本文件与顶层设计文档。
- 新增 L4 规范必须更新 `constraints/workflows-spec/l4-memory/README.md` 与上层索引。
