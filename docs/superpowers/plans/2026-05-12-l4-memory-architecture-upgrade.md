# L4 记忆系统架构升级方案 v2.0

> 状态: Draft | 日期: 2026-05-12 | 作者: 系统架构
> 本文档定义记忆系统的完整升级蓝图，作为重要地基文档供进一步调研和实现参考。

---

## 一、现状盘点

### 1.1 当前 L4 系统已有能力

| 模块 | 文件 | 功能 |
|---|---|---|
| 路径配置 | `paths.py` | 统一目录配置 |
| Agent 权限 | `agent_acl.py` | ACL 访问控制 |
| 案例注册 | `case_registry.py` | Episode → TradeCase 注册 |
| 象限迁移 | `quadrant_migrator.py` | x/y 坐标计算与更新 |
| 失败分析 | `failure_analyzer.py` | 亏损案例聚类 → 风险信号 |
| 蒸馏模板 | `distill_template.py` | 创建 Distill 骨架 |
| 索引构建 | `index_builder.py` | 搜索特征提取 |
| 相似查询 | `query_similar.py` | 三维相似度匹配 |
| 统计构建 | `stats_builder.py` | 聚合快照 |
| 仪表盘 | `dashboard_renderer.py` | Plotly HTML 渲染 |
| 内存总线 | `shared_memory_bus.py` | JSONL 事件通信 |
| 记忆图谱 | `memory_graph.py` | Agent-记忆关系图 |
| 元学习 | `meta_learning_tasks.py` | 假设验证/回测任务调度 |
| 迁移映射 | `migration_mapper.py` | 跨市场风险映射 |

### 1.2 当前数据模型

- **TradeCase** (`.workbuddy/memory_l4/schemas/trade_case.schema.json`): 交易案例，包含 intent/investigation/plan/execution/review/quadrant
- **Distill** (`.workbuddy/memory_l4/schemas/distill.schema.json`): 蒸馏教训，包含 kind/claim/supporting_case_ids/actionable_rules/quadrant
- **Stats** (`.workbuddy/memory_l4/schemas/stats.schema.json`): 聚合统计快照

### 1.3 当前象限体系

- **X 轴 (-1 → +1)**: 伤害 → 受益，从 PnL 推导（5% = 1.0）
- **Y 轴 (0 → 1)**: 确定性强度 = 0.4×perf + 0.4×consistency + 0.2×human
- **一致性阶梯**: 1→0.2, 2→0.35, 3→0.5, 5→0.65, 8→0.75, 13→0.85, 21→0.95, 21+→1.0

### 1.4 当前缺口

| 缺口 | 说明 | 优先级 |
|---|---|---|
| A0-A9 思维链缺失 | TradeCase.plan.steps 只是字符串数组，无法承载完整决策证据链 | P0 |
| 实时检索缺失 | L1 仅有文件存储，无实时检索接口 | P0 |
| 复盘仅分析失败 | failure_analyzer 只处理 pnl<0 案例，缺少成功分析 | P0 |
| 蒸馏过于简单 | distill_template 只生成骨架，无 what/why/how 三层逻辑 | P0 |
| A7/A8 无桥接 | 理论与实践 SKILL 输出未接入 L4 消费管道 | P1 |
| 索引不支持思维链 | index_builder 不提取 thinking_chain 特征 | P1 |

---

## 二、升级后的完整架构

### 2.1 总体架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                        A0-A9 交易系统                          │
│  A0矛盾 A1调研 A2第一性 A3模拟 A4验证 A5执行                    │
│  A6监控 A7实践理论 A8理论验证 A9离场                            │
│         │                                      ▲               │
│         │ 调用记忆                             │ 反馈结果       │
├─────────┼──────────────────────────────────────┼───────────────┤
│         ▼                                      │               │
│  ┌──────────────┐    ┌──────────────────┐      │               │
│  │  L1 实时检索  │───→│  L4 记忆引擎     │──────┘               │
│  │  (毫秒~秒级)  │    │  (分钟~小时级)   │                      │
│  └──────┬───────┘    └──────┬───────────┘                      │
│         │                   │                                   │
│         │  共享 TradeCase 格式，L1 侧重实时查询，L4 侧重深度加工 │
└─────────┼───────────────────┼───────────────────────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      记忆数据层 (统一存储)                       │
│                                                                 │
│  .workbuddy/memory_l4/                                         │
│  ├── cases/          ← TradeCase JSON (L1/L4 共享)             │
│  ├── distills/       ← Distill JSON                            │
│  ├── reviews/        ← ReviewRecord JSON (新增)                │
│  ├── episodes/       ← Episode 原始数据                        │
│  ├── indexes/        ← 索引文件                                │
│  └── stats/          ← 聚合统计                                │
│                                                                 │
│  artifacts/memory_l4/                                          │
│  ├── shared_bus/     ← 事件总线 JSONL                          │
│  ├── graph/          ← 记忆图谱                                │
│  ├── failure_analysis/ ← 分析产物                              │
│  └── dashboard/      ← HTML 仪表盘                             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 L1 vs L4 职责边界

| 维度 | L1 实时检索层 | L4 记忆引擎层 |
|---|---|---|
| **延迟要求** | 毫秒~秒级 | 分钟~小时级 |
| **触发时机** | A0-A9 各阶段实时调用 | 交易闭环后 / 定时批量 |
| **查询模式** | 相似度检索、条件过滤 | 象限迁移、失败/成功分析、蒸馏 |
| **写入频率** | 每次交易闭环写入 | 批量加工时写入 |
| **数据格式** | TradeCase (完整或子集) | TradeCase → Distill → ReviewRecord |
| **核心接口** | `query_similar()`, 条件检索 | `review_engine()`, `distill_engine()`, `quadrant_migration()` |

**关键设计决策**: L1 和 L4 **共享同一个 TradeCase 格式**，L1 存储完整的 TradeCase JSON 文件，L4 在此基础上进行深度加工（复盘、蒸馏、象限迁移）。L1 的实时检索能力通过索引 + 快速查询接口实现，不需要额外的数据格式。

### 2.3 完整数据流

```
                    ┌─────────────────────────────────────────────┐
                    │            交易事件闭环 (A0-A9)              │
                    │  矛盾识别→调研→第一性→模拟→验证→执行→监控→离场│
                    └─────────────────────┬───────────────────────┘
                                          │
                            Episode 数据落地
                                          │
                                          ▼
                    ┌──────────────────────────────────┐
                    │  L1: case_registry (注册 TradeCase)│
                    │  - 创建完整 TradeCase JSON        │
                    │  - 包含 thinking_chain (A0-A9)    │
                    │  - 包含 evidence_chain (证据链)   │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │                              │
                    ▼                              ▼
        ┌───────────────────────┐    ┌────────────────────────┐
        │  L1 实时检索服务       │    │  L4 记忆引擎 (批量)     │
        │  - 索引构建            │    │                        │
        │  - 相似案例查询        │    │  ┌──────────────────┐  │
        │  - 条件过滤查询        │    │  │ review_engine    │  │
        │  - A0-A9 阶段调用     │    │  │ (对错双向分析)    │  │
        └───────────────────────┘    │  └────────┬─────────┘  │
                    ▲               │           ▼             │
                    │               │  ┌──────────────────┐  │
                    │               │  │ distill_engine   │  │
                    │ 查询参考       │  │ (11步+三问)      │  │
                    │               │  └────────┬─────────┘  │
                    │               │           ▼             │
                    │               │  ┌──────────────────┐  │
                    │               │  │ quadrant_migrator│  │
                    │               │  │ (四象限量化)     │  │
                    │               │  └────────┬─────────┘  │
                    │               │           ▼             │
                    │               │  ┌──────────────────┐  │
                    │               │  │ migration_mapper │  │
                    │               │  │ (跨市场迁移)     │  │
                    │               │  └────────┬─────────┘  │
                    │               │           ▼             │
                    │               │  ┌──────────────────┐  │
                    │               │  │ meta_learning    │  │
                    │               │  │ (元学习任务调度)  │  │
                    │               │  └──────────────────┘  │
                    │               └────────────────────────┘
                    └──────────────────────────────────────────┘
```

---

## 三、Schema 升级设计

### 3.1 TradeCase v0.2 升级

**核心改动**: 新增 `thinking_chain` 和 `evidence_chain`，其余字段向后兼容。

```
TradeCase (v0.2)
├── case_id, version, ts_start, ts_end, inst_id, tags  [不变]
├── intent                                              [不变]
├── investigation                                       [不变]
├── theory_refs                                         [不变]
├── environment_snapshot                                [不变]
│
├── thinking_chain        ←──────── 新增，A0-A9 完整思维链
│   └── [{
│         stage,            // "A0" ~ "A9"，实际执行过的阶段
│         ts,               // 该阶段时间戳
│         decision,         // 该阶段做出的决策
│         rationale,        // 决策理由
│         contradiction,    // A0 专用：识别到的矛盾
│         contradiction_analysis,  // A0/A8 专用：矛盾分析
│         hypothesis,       // A3/A4 专用：假设
│         test_result,      // A4/A8 专用：测试结果
│         exit_logic,       // A9 专用：离场逻辑
│         evidence_refs,    // 该阶段证据引用
│         stage_output_ref  // 该阶段产出文件引用
│       }]
│
├── evidence_chain          ←──────── 新增，完整决策证据链
│   ├── market_data_refs    // 市场数据引用
│   ├── signal_refs         // 信号/指标引用
│   ├── strategy_refs       // 策略文档引用
│   ├── historical_refs     // 历史案例引用 (指向其他 TradeCase)
│   └── constraint_refs     // 约束/规则引用
│
├── plan                    [不变]
├── execution               [不变]
├── online_pressure_test    [不变]
├── rollout_monitoring      [不变]
├── backtest                [不变]
├── review                  [扩展]
│   ├── summary             [不变]
│   ├── theory_practice_consistency  [不变]
│   ├── lessons             [不变]
│   ├── mistakes            ← 新增: [{what, why, severity, stage_ref}]
│   ├── successes           ← 新增: [{what, where_right, stage_ref}]
│   └── review_record_id    ← 新增: 指向 ReviewRecord 的引用
│
├── dream_reflection        [不变]
└── quadrant                [不变]
```

### 3.2 Distill v0.2 升级

**核心改动**: 新增 `what_is_it`、`why_it_works`、`how_to_apply`、`process_trace`，保持向后兼容（原有 `claim` 作为 `what_is_it.claim` 的快捷引用）。

```
Distill (v0.2)
├── distill_id, version  [不变]
│
├── kind                  [扩展枚举]
│   └── "benefit_experience" | "risk_signal" | "decision_heuristic"
│       | "contradiction_pattern" | "exit_logic" | "theory_update"
│
├── what_is_it            ←──────── 新增: "是什么"
│   ├── claim             // 核心主张 (兼容旧版顶层 claim)
│   ├── definition        // 定义
│   └── classification    // 分类标签
│
├── why_it_works          ←──────── 新增: "为什么"
│   ├── causal_analysis   // 因果分析
│   ├── theory_basis      // 理论基础 (引用知识库/理论)
│   ├── evidence_chain    // 证据链 (引用支持案例)
│   └── contradiction_resolved  // 解决的矛盾
│
├── how_to_apply          ←──────── 新增: "怎么做"
│   ├── actionable_rules  // 可操作规则 (兼容旧版顶层 actionable_rules)
│   ├── trigger_conditions  // 触发条件
│   ├── step_by_step      // 逐步操作指南
│   └── risk_warnings     // 风险警告
│
├── supporting_case_ids   [不变]
├── claim                 [保留，兼容旧版，等同于 what_is_it.claim]
├── actionable_rules      [保留，兼容旧版，等同于 how_to_apply.actionable_rules]
│
├── process_trace         ←──────── 新增: 11步蒸馏流程追溯
│   ├── intent            // 意图: 明确问题
│   ├── investigation     // 调研: 现状调查与矛盾分析
│   ├── theory_refs       // 理论: 知识库+历史事件+联网搜索
│   ├── hypothesis        // 假设: 基于矛盾分析、现状、理论
│   ├── test_results      // 测试与观测: 验证假设，搜集数据
│   ├── conclusion        // 结论: 根据假设与实际表现推导
│   ├── implementation    // 落地: 实施方案
│   ├── monitoring        // 监控: 监控结果
│   ├── review_result     // 复盘: 理论与实践一致性检验
│   ├── reflection        // 做梦: 外部反思
│   └── optimization      // 更新优化: 最终优化方案
│
├── quadrant              [不变]
└── migration_history     [不变]
```

### 3.3 ReviewRecord (全新)

**定位**: 复盘引擎输出，连接 L1 TradeCase 与 L4 Distill 的桥梁。

```
ReviewRecord (v0.1)
├── review_id             // "REV_{timestamp}_{case_id}"
├── version               // "v0.1"
├── snapshot_ts           // 复盘时间戳
├── case_id               // 关联的 TradeCase
├── direction             // "success" | "failure" | "mixed"
│
├── mistakes              // [{
│     what,               // 做错了什么
│     why,                // 为什么错 (根因)
│     severity,           // 严重程度 0-1
│     stage_ref,          // 关联 A0-A9 阶段
│     theory_gap          // 理论与实践的差距
│   }]
│
├── successes             // [{
│     what,               // 做对了什么
│     where_right,        // 哪里对 (理论依据)
│     stage_ref,          // 关联 A0-A9 阶段
│     reproducible        // 是否可复现
│   }]
│
├── theory_practice_analysis  // A8 理论验证深度分析
│   ├── consistency_score     // 一致性评分 0-1
│   ├── confirmed_theories    // 被实践证实的理论
│   ├── contradicted_theories // 被实践证伪的理论
│   └── gap_analysis          // 差距分析
│
├── distill_proposals     // 蒸馏建议: [{distill_kind, claim, confidence}]
├── quadrant              // 复盘记录的象限坐标 (复用 quadrant schema)
└── a7_report_ref         // A7 实践理论报告引用
    └── a8_report_ref     // A8 理论验证报告引用
```

### 3.4 版本兼容性策略

- TradeCase `v0.1` 文件可被 v0.2 读取器处理（新字段缺失时使用默认值）
- TradeCase `v0.2` 写入器在保存 v0.1 文件时，新字段写入默认空值
- `thinking_chain` 和 `evidence_chain` 为可选字段，v0.1 文件不存在这两个字段不影响现有查询
- Distill 保留顶层 `claim` 和 `actionable_rules` 作为兼容层，同时读取时也填充 `what_is_it` / `how_to_apply`

---

## 四、核心模块升级设计

### 4.1 Phase 1: 记忆底层 — TradeCase + 索引升级

#### 4.1.1 TradeCase Schema 扩展

- 文件: `.workbuddy/memory_l4/schemas/trade_case.schema.json` → v0.2
- 新增 `thinking_chain` 数组字段，每个元素对应 A0-A9 一个阶段的结构化记录
- 新增 `evidence_chain` 对象，包含市场数据/信号/策略/历史案例/约束的引用
- `review` 对象新增 `mistakes[]`、`successes[]`、`review_record_id`

#### 4.1.2 case_registry 增强

- 文件: `scripts/memory_l4/case_registry.py`
- 改动:
  - `create_case_from_episode_data()`: 新增 thinking_chain 初始化（空数组）
  - 新增 `populate_thinking_chain(case, stage_records)`: 将 A0-A9 各阶段产出填充到 thinking_chain
  - 新增 `populate_evidence_chain(case, evidence_refs)`: 将各类证据引用填充到 evidence_chain
  - 版本标识从 `v0.1` 升级到 `v0.2`

#### 4.1.3 索引构建升级

- 文件: `scripts/memory_l4/index_builder.py`
- 改动:
  - 新增提取 thinking_chain 特征：各阶段 stage、decision、contradiction
  - 新增提取 evidence_chain 特征：引用类型分布
  - 新增 A0-A9 阶段覆盖度统计（哪些阶段有数据，哪些缺失）
  - 索引文件新增 `thinking_features` 和 `evidence_features` 字段

#### 4.1.4 L1 实时检索接口

- 文件: `scripts/memory_l4/query_similar.py` (扩展)
- 新增接口:
  - `query_by_stage(stage_id, top_k)`: 按 A0-A9 阶段检索案例
  - `query_by_regime_and_outcome(regime, outcome_direction, top_k)`: 按市场状态+结果方向检索
  - `query_by_tags(tags, top_k)`: 按标签检索
  - `get_evidence_chain(case_id)`: 获取完整证据链
  - `get_thinking_chain(case_id)`: 获取完整思维链

#### 4.1.5 A0-A9 → L1 数据通道

- 文件: 新建 `scripts/memory_l4/a0a9_bridge.py`
- 功能:
  - `collect_stage_outputs(trace_id)`: 从 artifacts/trading/ 收集 A0-A9 各阶段产出
  - `build_thinking_chain_from_stages(stage_outputs)`: 将阶段产出转换为 thinking_chain 格式
  - `enrich_case_with_stages(case_id, stage_outputs)`: 将阶段数据填充到已存在的 TradeCase
  - `query_memory_for_stage(stage_id, context)`: A0-A9 阶段调用 L1 检索历史参考

### 4.2 Phase 2: 复盘引擎 — 对错双向分析

#### 4.2.1 ReviewRecord Schema

- 文件: 新建 `.workbuddy/memory_l4/schemas/review.schema.json`
- 定义如 3.3 节所示

#### 4.2.2 Review Engine

- 文件: 新建 `scripts/memory_l4/review_engine.py`
- 功能:
  - `analyze_success(cases, episodes_by_case_id)`: 成功案例分析 → 成功经验信号
  - `analyze_failure(cases, episodes_by_case_id)`: 失败案例分析 (复用 failure_analyzer 逻辑)
  - `analyze_mixed(cases, episodes_by_case_id)`: 混合分析（盈亏并存）
  - `build_review_record(case, analysis, a7_report, a8_report)`: 构建 ReviewRecord
  - `run_review(snapshot_ts, cases, episodes_by_case_id)`: 批量复盘
- 保留 `failure_analyzer.py` 作为 review_engine 的子模块导入

#### 4.2.3 A7/A8 报告桥接

- 文件: 新建 `scripts/memory_l4/a7a8_bridge.py`
- 功能:
  - `parse_a7_report(report_path)`: 解析 A7 实践理论报告 → 标准化格式
  - `parse_a8_report(report_path)`: 解析 A8 理论验证报告 → 标准化格式
  - `merge_into_review(review_record, a7_parsed, a8_parsed)`: 合并到 ReviewRecord

### 4.3 Phase 3: 蒸馏升级 — 11步流程 + 三问逻辑

#### 4.3.1 Distill Schema 扩展

- 文件: `.workbuddy/memory_l4/schemas/distill.schema.json` → v0.2
- 新增 `what_is_it`、`why_it_works`、`how_to_apply`、`process_trace`
- `kind` 枚举扩展

#### 4.3.2 Distill Engine

- 文件: 新建 `scripts/memory_l4/distill_engine.py`
- 功能:
  - `start_distill(review_record)`: 从 ReviewRecord 启动蒸馏流程
  - `step_intent(review, distill)`: 明确问题
  - `step_investigation(review, distill)`: 现状调查与矛盾分析
  - `step_theory(distill)`: 调用知识库/历史事件/联网搜索
  - `step_hypothesis(distill)`: 生成假设
  - `step_test(distill)`: 测试与观测
  - `step_conclusion(distill)`: 推导结论
  - `step_implementation(distill)`: 落地
  - `step_monitoring(distill)`: 监控
  - `step_review(distill)`: 理论与实践一致性检验
  - `step_reflection(distill)`: 外部反思（做梦）
  - `step_optimization(distill)`: 更新优化
  - `answer_what_is_it(distill)`: 回答"是什么"
  - `answer_why_it_works(distill)`: 回答"为什么"
  - `answer_how_to_apply(distill)`: 回答"怎么做"
  - `complete_distill(distill)`: 完成蒸馏，计算象限坐标

#### 4.3.3 distill_template 兼容

- 文件: `scripts/memory_l4/distill_template.py`
- 改动: 保留原有 CLI 接口，内部调用 distill_engine 的完整流程

### 4.4 Phase 4: 统计驱动闭环

#### 4.4.1 四象限静态事件库

- 在现有 stats 基础上，新增 `event_library` 分类
- 按 (regime, category, x_range, y_range) 四维索引
- 构建 `event_library_index` 支持 A0-A9 快速查询:
  - `query_library(regime, category, min_x, min_y)`: 返回符合条件的案例/Distill
  - `get_evolution_path(distill_id)`: 获取蒸馏记录的置信度演化路径

#### 4.4.2 动态演化趋势

- 扩展 `stats_builder.py`:
  - 新增 `compute_evolution_metrics()`: 计算蒸馏记录的 y 轴演化速率、稳定性
  - 新增 `identify_emerging_patterns()`: 识别正在形成的新模式（新聚集的象限区域）
  - 新增 `pattern_maturity_score()`: 模式成熟度评分（案例数 × 一致性 × 时间跨度）

#### 4.4.3 象限体系增强

- 保持 x/y 核心不变
- 新增第三维标签过滤（非坐标轴）:
  - `regime`: 市场状态
  - `category`: 交易类型
  - `severity`: 影响程度
- 在 stats.points 中新增 `category` 和 `severity` 字段

---

## 五、文件变更清单

### 5.1 Schema 文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `trade_case.schema.json` | 修改 | 新增 thinking_chain, evidence_chain, review 扩展 |
| `distill.schema.json` | 修改 | 新增 what/why/how, process_trace, kind 扩展 |
| `review.schema.json` | 新建 | ReviewRecord 完整定义 |
| `stats.schema.json` | 修改 | 新增 event_library, category, severity |

### 5.2 Python 模块

| 文件 | 操作 | Phase | 说明 |
|---|---|---|---|
| `case_registry.py` | 修改 | P1 | thinking_chain/evidence_chain 初始化 |
| `index_builder.py` | 修改 | P1 | 思维链特征提取 |
| `query_similar.py` | 修改 | P1 | 新增 L1 实时检索接口 |
| `a0a9_bridge.py` | 新建 | P1 | A0-A9 数据通道 |
| `review_engine.py` | 新建 | P2 | 对错双向复盘 |
| `a7a8_bridge.py` | 新建 | P2 | A7/A8 报告桥接 |
| `distill_engine.py` | 新建 | P3 | 11步流程 + 三问蒸馏 |
| `failure_analyzer.py` | 保留 | P2 | 作为 review_engine 子模块 |
| `quadrant_migrator.py` | 修改 | P4 | 支持新字段 |
| `stats_builder.py` | 修改 | P4 | 演化指标 + 事件库 |
| `distill_template.py` | 修改 | P3 | 兼容层调用 distill_engine |

### 5.3 目录结构变更

```
.workbuddy/memory_l4/schemas/
├── trade_case.schema.json        (修改 → v0.2)
├── distill.schema.json           (修改 → v0.2)
├── stats.schema.json             (修改)
└── review.schema.json            (新建)

scripts/memory_l4/
├── __init__.py
├── paths.py                      (不变)
├── agent_acl.py                  (不变)
├── case_registry.py              (修改)
├── index_builder.py              (修改)
├── query_similar.py              (修改)
├── a0a9_bridge.py                (新建)
├── review_engine.py              (新建)
├── a7a8_bridge.py                (新建)
├── distill_engine.py             (新建)
├── failure_analyzer.py           (保留，作为子模块)
├── distill_template.py           (修改)
├── quadrant_migrator.py          (修改)
├── stats_builder.py              (修改)
├── dashboard_renderer.py         (不变)
├── shared_memory_bus.py          (不变)
├── memory_graph.py               (不变)
├── meta_learning_tasks.py        (不变)
└── migration_mapper.py           (不变)
```

---

## 六、实施优先级

### P0 — 地基 (必须先行)

1. **TradeCase Schema v0.2**: thinking_chain + evidence_chain + review 扩展
2. **case_registry 增强**: 初始化新字段
3. **索引升级**: 思维链特征提取
4. **L1 实时检索接口**: query_by_stage, query_by_regime, get_thinking_chain
5. **A0-A9 数据桥**: collect_stage_outputs → enrich TradeCase
6. **ReviewRecord Schema**: 定义复盘输出格式

### P1 — 复盘引擎

7. **review_engine.py**: 对错双向分析
8. **A7/A8 桥接**: 理论与实践报告接入
9. **failure_analyzer 重构**: 作为 review_engine 子模块

### P2 — 蒸馏升级

10. **Distill Schema v0.2**: what/why/how + process_trace
11. **distill_engine.py**: 11步流程 + 三问
12. **distill_template 兼容**: 保留 CLI

### P3 — 统计驱动闭环

13. **静态事件库**: 四象限分类 + A0-A9 查询接口
14. **动态演化**: y 轴演化速率 + 新模式识别
15. **Stats 升级**: 新字段 + 事件库索引

---

## 七、关键设计决策记录

### 7.1 为什么 L1 和 L4 共享 TradeCase？

- **一致性**: 避免数据格式转换的复杂度和丢失信息的风险
- **实时性**: L1 的 TradeCase 文件天然就是可检索的，通过索引加速即可实现秒级响应
- **完整性**: 一个 TradeCase 包含交易的完整闭环，L1 可以按需返回全部或子集

### 7.2 为什么 thinking_chain 是数组而不是嵌套对象？

- **灵活性**: 不同交易可能只经过部分 A0-A9 阶段，数组只记录实际执行的阶段
- **有序性**: 数组天然保持阶段执行顺序
- **可扩展**: 同一阶段可能多次执行（如 A6 多次触发），数组可以追加

### 7.3 为什么复盘独立为 ReviewRecord 而不是直接修改 TradeCase？

- **审计性**: 复盘是一个独立的时间点行为，与交易本身的时间线分开
- **多版本**: 同一 TradeCase 可能经过多次复盘，每次复盘产生独立记录
- **桥接**: ReviewRecord 天然连接 TradeCase 和 Distill，是 L4 管道的中间产物

### 7.4 为什么 Distill 保留顶层 claim 和 actionable_rules？

- **向后兼容**: 现有代码直接访问这两个字段，不需要批量迁移
- **快捷引用**: 对于不需要完整 what/why/how 的场景，顶层字段足够
- **渐进升级**: 新代码优先使用 what_is_it/how_to_apply，旧代码不受影响

---

## 八、风险与注意事项

| 风险 | 说明 | 缓解 |
|---|---|---|
| Schema 兼容性 | v0.2 写入器可能破坏 v0.1 读取器 | 新字段全为 optional，v0.1 读取器忽略新字段 |
| 索引性能 | thinking_chain 特征增加索引大小 | 初始阶段案例数量有限，性能可控；后续考虑向量数据库 |
| A7/A8 格式不稳定 | A7/A8 报告格式可能变化 | a7a8_bridge 使用宽松解析，缺失字段用默认值 |
| 蒸馏流程复杂度 | 11步流程可能难以自动化 | 先实现核心步骤 (intent→hypothesis→conclusion)，其余逐步迭代 |
| 四象限过度简化 | x/y 可能不足以区分复杂模式 | 增加标签过滤维度，但保持 x/y 核心不变 |

---

## 九、验收标准

### Phase 1 (P0) 验收

- [ ] TradeCase v0.2 schema 通过 JSON Schema 校验
- [ ] 新建的 TradeCase 自动初始化 thinking_chain (空数组) 和 evidence_chain
- [ ] 索引文件包含 thinking_features 和 evidence_features
- [ ] `query_by_stage("A0")` 返回包含 A0 阶段数据的案例
- [ ] `get_thinking_chain(case_id)` 返回完整思维链
- [ ] A0-A9 阶段产出可以被收集并填充到 TradeCase

### Phase 2 (P1) 验收

- [ ] review_engine 对成功和失败案例都能生成 ReviewRecord
- [ ] ReviewRecord 包含 mistakes[] 和 successes[]
- [ ] A7/A8 报告可以被解析并合并到 ReviewRecord
- [ ] ReviewRecord 通过 JSON Schema 校验

### Phase 3 (P2) 验收

- [ ] Distill v0.2 schema 通过 JSON Schema 校验
- [ ] distill_engine 可以完成完整的 11 步流程
- [ ] 每个蒸馏记录回答"是什么"、"为什么"、"怎么做"
- [ ] 旧版 Distill 文件可以被 v0.2 读取器处理

### Phase 4 (P3) 验收

- [ ] 四象限静态事件库可被 A0-A9 查询
- [ ] 演化指标计算正确
- [ ] 新模式识别功能可以检测到新聚集的象限区域
- [ ] 仪表盘展示新字段
