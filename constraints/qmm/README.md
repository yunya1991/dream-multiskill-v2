# QMM 记忆量化模块规范目录

本目录用于集中管理 QMM（Quantitative Memory Model）记忆量化系统的底层约束与设计规范。

QMM 是 L4 记忆系统的**可插拔量化内核**，不是替代 L1-L4 的新总架构。
- L4 = 认知层（事件→复盘→蒸馏→统计），产出 TradeCase/Review/Distill/Stats
- QMM = 量化内核，只读 L4 产出物，提炼数学信号输出固定契约

## 仓库演进策略

| 仓库 | 阶段 | 能力范围 | 依赖 |
|------|------|----------|------|
| V2 (dream-multiskill-v2) | Phase 1+2 | 确定性基线 + 在线门禁 | math/statistics 仅标准库 |
| V3 (独立仓库) | Phase 3 | ML 训练闭环 + 过拟合/漂移 | numpy/sklearn/scipy |
| V4 (独立仓库) | Phase 4 | QMM V2 内核 + 表征学习 | 完整 ML 栈 |

V2 完成 Phase 1+2 后停止进化，Phase 3/4 在 V3/V4 并行研究。

## 文件索引

### 总架构
- `architecture.md`：QMM 总架构设计（修正版，消除所有矛盾点）

### 阶段设计
- `phase-1.md`：Stage 1 — QMM 离线内核（V2 仓库，纯 math/statistics）
- `phase-2.md`：Stage 2 — QMM 在线门禁（V2 仓库，回测验证 + A 系列消费）
- `phase-3.md`：Stage 3 — V3 仓库 + ML 训练闭环（numpy/sklearn）
- `phase-4.md`：Stage 4 — V4 仓库 + QMM V2 内核（完整量化内核）

### 基础规范
- `version-triple-spec.md`：版本三元组规范（data_version / feature_def_version / qmm_version）

### 远景
- `qmm-v5-vision.md`：QMM V5 终极愿景（原 PR #48，不受约束的完整设计空间探索）

## 主从映射

- 顶层总架构（主）：`constraints/qmm/architecture.md`
- 阶段设计（主）：`constraints/qmm/phase-{1,2,3,4}.md`
- 实现代码（从）：V2 `scripts/memory_l4/qmm/` → V3/V4 独立仓库

## 与 L4 的关系

- L4 工程架构：`constraints/workflows-spec/l4-memory/architecture-and-workflow-design.md`
- QMM 不修改 L4 schema，不接管 L1-L4 主链路
- QMM 只读 L4 产出物（cases/distills/stats/index），输出到独立 `qmm/` 目录
- A 系列通过可选 import 消费 QMM 信号，不改变现有 entrypoint 逻辑

## QMM 输出契约（固定）

```
trend_state          趋势状态 (UP / DOWN / FLAT / TRANSITIONING)
trend_change_point   趋势变化点 (ACCELERATING / DECELERATING / REVERSING / STABLE)
mrd_vector           阻力最小方向向量 {direction, resistance_up, resistance_down, confidence}
uncertainty          不确定性量化 (0-1)
reason_codes         原因代码 (英文大写枚举，如 BULLISH_ALIGNMENT, HIGH_UNCERTAINTY)
evidence_refs        证据引用 (指向 TradeCase/Distill ID)
```
