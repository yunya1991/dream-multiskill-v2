# Dream-MultiSkill A0-A9 通信协议与三大闭环架构

> **文档版本**: v2.0 (基于实际三大闭环架构)  
> **更新时间**: 2026-05-11  
> **架构**: 执行环 + 情报环 + 治理环（三环嵌套）

---

## 📋 目录

1. [三大核心闭环架构](#三大核心闭环架构)
2. [通信协议规范](#通信协议规范)
3. [闭环触发机制](#闭环触发机制)
4. [消息格式定义](#消息格式定义)
5. [状态机与转换](#状态机与转换)
6. [处罚与重试机制](#处罚与重试机制)
7. [实现示例](#实现示例)

---

## 三大核心闭环架构

### 架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Dream-MultiSkill                          │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    🟣 治理环 (Governance Loop)               │  │
│  │           A0 → A7 → A8 (理论闭环)                          │  │
│  │           - A0: 矛盾监控                                    │  │
│  │           - A7: 实践记录                                    │  │
│  │           - A8: 理论验证 (知行合一)                         │  │
│  │           - 触发: A7完成后 / 每日14:00                     │  │
│  └────────────────────────┬────────────────────────────────────┘  │
│                           │ 驱动                                  │
│  ┌────────────────────────▼────────────────────────────────────┐  │
│  │                  🔵 执行环 (Execution Loop)                 │  │
│  │         A1 → A2 → A3 → A4 → A5 → A9                     │  │
│  │         - A1: 深度调研                                     │  │
│  │         - A2: 第一性原理分析                               │  │
│  │         - A3: 策略设计                                     │  │
│  │         - A4: 战术验证                                     │  │
│  │         - A5: 战术执行                                     │  │
│  │         - A9: 离场决策                                     │  │
│  │         - 触发: A0信号 / 定时任务                          │  │
│  └────────────────────────┬────────────────────────────────────┘  │
│                           │ 监控                                  │
│  ┌────────────────────────▼────────────────────────────────────┐  │
│  │                🟠 情报环 (Intelligence Loop)                │  │
│  │                        A6 (中枢)                            │  │
│  │        5级放射驱动:                                         │  │
│  │        L0致命 → A9 (离场)                                 │  │
│  │        L1高 → A4 (验证)                                   │  │
│  │        L1.5变 → A2 (增量更新)                             │  │
│  │        L2中 → 观察                                        │  │
│  │        L3背离 → A1+A3 (重启)                              │  │
│  │        - 触发: 每小时 / 事件驱动                          │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 1️⃣ 执行环 (Execution Loop) - 蓝色

#### 职能
正向执行交易决策，从调研到执行的完整链路。

#### 模块序列
```
A1 (调研) → A2 (分析) → A3 (策略) → A4 (验证) → A5 (执行) → A9 (离场)
```

#### 闭环特性
- **正向流**: A1→A2→A3→A4→A5→A9
- **反馈点**:
  - A4 验证失败 → 返回 A3 (策略调整)
  - A5 执行失败 → 返回 A4 (重新验证)
  - A9 离场 → 触发 A7 (实践记录)

#### 通信模式
- **同步调用**: A1→A2→A3→A4→A5 (串行)
- **异步通知**: A5→A6 (执行结果通知)
- **事件驱动**: A9→All (离场事件)

#### 状态转换
```
[IDLE] → A0信号 → [RESEARCH] (A1) → [ANALYZING] (A2) → [STRATEGIZING] (A3)
       → [VALIDATING] (A4) → [EXECUTING] (A5) → [MONITORING] (A6) → [EXIT] (A9)
       → [PRACTICE] (A7) → [VERIFICATION] (A8) → [IDLE]
```

---

### 2️⃣ 情报环 (Intelligence Loop) - 琥珀色

#### 职能
A6 作为中枢，5级放射驱动其他模块，实现实时监控与响应。

#### A6 中枢 5 级放射驱动

| 级别 | 触发条件 | 目标模块 | 动作 | 优先级 |
|------|----------|----------|------|--------|
| **L0 致命** | 风险事件 / 黑天鹅 | A9 | 立即离场 | CRITICAL |
| **L1 高** | 重大变化 / 验证失败 | A4 | 重新验证 | HIGH |
| **L1.5 变** | Regime 变化 | A2 | 增量更新 | HIGH |
| **L2 中** | 异常信号 | 观察 | 记录日志 | MEDIUM |
| **L3 背离** | 理论与实践背离 | A1+A3 | 重启调研 | MEDIUM |

#### 反馈闭环

```
                    ┌───────────────────────────────┐
                    │       A6 情报监控             │
                    │  (每小时运行)                │
                    └──────┬────────────┬─────────┘
                           │            │
              ┌────────────▼──────┐  │
              │  5级放射驱动      │  │
              └──────┬──────────┘  │
                     │              │
       ┌─────────────┼──────────────┼─────────────┐
       │             │              │             │
       ▼             ▼              ▼             ▼
  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
  │A9 离场  │   │A4 验证  │   │A2 更新  │   │A1+A3  │
  │(L0致命) │   │(L1高)   │   │(L1.5变)│   │重启    │
  └───┬────┘   └───┬────┘   └───┬────┘   └───┬────┘
      │               │              │              │
      └───────────────┴──────────────┴──────────────┘
                     │
                     ▼
              ┌──────────────┐
              │  执行环重启   │
              │  (A1→A5)    │
              └──────────────┘
```

#### 通信模式
- **发布/订阅**: A6 发布情报，其他模块订阅
- **事件驱动**: L0-L3 事件触发相应模块
- **异步推送**: A6 → A1/A2/A3/A4/A9

#### 定时触发
```yaml
schedule: "0 * * * *"  # 每小时
timeout: 300
retry: 3
```

---

### 3️⃣ 治理环 (Governance Loop) - 紫色

#### 职能
实现理论与实践的结合验证，推动系统进化。

#### 模块序列
```
A0 (矛盾监控) → A7 (实践记录) → A8 (理论验证) → A2/A3 (理论修正)
```

#### 理论闭环 (A7-A8 内部循环)

```
┌─────────────────────────────────────────────────────────────┐
│                                🟣 理论闭环                  │
│  ┌─────────────────┐                                   │
│  │  实践 (A7)        │                                   │
│  │  - 记录执行过程    │                                   │
│  │  - 提炼经验教训    │                                   │
│  └────────┬────────┘                                   │
│           │ 实践记录                                      │
│           ▼                                              │
│  ┌─────────────────┐                                   │
│  │  理论 (A8)        │                                   │
│  │  - 知行合一检查    │                                   │
│  │  - 批判性分析      │                                   │
│  │  - 理论修正建议    │                                   │
│  └────────┬────────┘                                   │
│           │ 验证结果                                      │
│           ▼                                              │
│  ┌─────────────────┐                                   │
│  │  修正 (A2/A3)      │                                   │
│  │  - 更新理论模型    │                                   │
│  │  - 优化策略逻辑    │                                   │
│  └────────┬────────┘                                   │
│           │ 理论更新                                      │
│           ▼                                              │
│  ┌─────────────────┐                                   │
│  │  下一轮实践 (A7)  │                                   │
│  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
```

#### 知行合一评分

| 评分 | 含义 | 动作 |
|------|------|------|
| **0.9-1.0** | 知行合一 | 继续 |
| **0.7-0.9** | 轻微背离 | 记录观察 |
| **0.5-0.7** | 中度背离 | 理论修正 |
| **<0.5** | 严重背离 | 重启 A2/A3 |

#### 通信模式
- **请求/响应**: A7→A8→A2/A3
- **批处理**: A8 每日 14:00 运行
- **异步通知**: A8→A2/A3 (理论修正通知)

#### 定时触发
```yaml
schedule: "0 14 * * *"  # 每日 14:00
timeout: 600
retry: 2
```

---

## 通信协议规范

### 1. 消息头规范 (Message Header)

所有模块间通信必须包含标准消息头：

```json
{
  "header": {
    "message_id": "msg_{source}_{timestamp}_{seq}",  // 全局唯一 ID
    "timestamp": "2026-05-11T10:10:30+08:00",      // ISO 8601 时间戳
    "version": "2.0",                                 // 协议版本 (更新为 2.0)
    "source": "A1",                                   // 源模块
    "target": "A2",                                   // 目标模块
    "type": "REQUEST",                                 // 消息类型
    "priority": "HIGH",                               // 优先级
    "correlation_id": "sig_20260511_1010",            // 关联 ID
    "trace_id": "trace_20260511_1010",               // 追踪 ID (全链路)
    "loop_type": "execution",                         // 所属闭环 (execution/intelligence/governance)
    "timeout_ms": 30000                                // 超时时间 (毫秒)
  },
  "payload": {
    // 消息体
  }
}
```

#### 新增字段说明

| 字段 | 说明 | 取值 |
|------|------|------|
| **loop_type** | 消息所属的闭环 | `execution` / `intelligence` / `governance` |
| **trace_id** | 全链路追踪 ID | 贯穿三大闭环的唯一 ID |

---

### 2. 消息类型 (Message Types)

| 类型 | 说明 | 是否需要响应 | 超时处理 | 适用闭环 |
|------|------|--------------|----------|----------|
| **REQUEST** | 请求消息 | ✅ 需要 | 触发重试/降级 | 执行环、治理环 |
| **RESPONSE** | 响应消息 | ❌ 不需要 | 忽略 | 执行环、治理环 |
| **NOTIFICATION** | 通知消息 | ❌ 不需要 | 记录日志 | 情报环 |
| **EVENT** | 事件消息 | ❌ 不需要 | 触发订阅者 | 情报环 |
| **HEARTBEAT** | 心跳消息 | ❌ 不需要 | 标记离线 | 所有闭环 |
| **ERROR** | 错误消息 | ❌ 不需要 | 触发处罚 | 所有闭环 |
| **FEEDBACK** | 反馈消息 | ❌ 不需要 | 触发理论修正 | 治理环 |

---

### 3. 传输协议 (Transport Protocol)

#### 方案 A：HTTP REST API (适用于执行环和治理环)

```yaml
协议: HTTP/1.1 或 HTTP/2
格式: JSON
认证: JWT Token
超时: 默认 30s，可配置
重试: 指数退避 (Exponential Backoff)
适用: 同步调用 (A1→A2→A3→A4→A5)
```

**端点规范**：
```bash
# 执行环
POST /a1/research
POST /a2/analysis
POST /a3/strategy
POST /a4/validation
POST /a5/execution
POST /a9/exit

# 情报环 (A6 中枢)
POST /a6/intelligence
POST /a6/alert

# 治理环
POST /a7/practice
POST /a8/verification
```

#### 方案 B：消息队列 (适用于情报环)

```yaml
消息队列: RabbitMQ / Apache Kafka / Redis Streams
格式: JSON
持久化: ✅ 开启
ACK 机制: ✅ 开启
重试: 死信队列 (DLQ)
适用: 异步通知 (A6 → A1/A2/A3/A4/A9)
```

**Topic 规范**：
```bash
# 执行环
dream.execution.a1.*                   # A1 调研
dream.execution.a2.*                   # A2 分析
dream.execution.a3.*                   # A3 策略
dream.execution.a4.*                   # A4 验证
dream.execution.a5.*                   # A5 执行
dream.execution.a9.*                   # A9 离场

# 情报环 (A6 中枢)
dream.intelligence.a6.alert            # A6 警报
dream.intelligence.a6.L0              # L0 致命 → A9
dream.intelligence.a6.L1              # L1 高 → A4
dream.intelligence.a6.L1.5            # L1.5 变 → A2
dream.intelligence.a6.L2              # L2 中 → 观察
dream.intelligence.a6.L3              # L3 背离 → A1+A3

# 治理环
dream.governance.a7.*                 # A7 实践
dream.governance.a8.*                 # A8 验证
dream.governance.a8.feedback          # A8 反馈 → A2/A3
```

---

## 闭环触发机制

### 1. 执行环触发机制

#### 触发类型

| 触发类型 | 触发源 | 目标模块 | 条件 |
|----------|----------|----------|------|
| **事件触发** | A0 | A1 | 矛盾信号检测 |
| **依赖触发** | A1 | A2 | A1 完成 |
| **依赖触发** | A2 | A3 | A2 完成 |
| **依赖触发** | A3 | A4 | A3 完成 |
| **依赖触发** | A4 | A5 | A4 通过 |
| **事件触发** | A5 | A6 | 执行结果 |
| **事件触发** | A9 | A7 | 离场完成 |

#### 触发流程

```
A0 信号检测
    ↓
[条件评估] → 满足条件？
    ↓ 是
[生成触发消息] → A0 → A1
    ↓
[A1 处理] → 完成？
    ↓ 是
[触发 A2] → A1 → A2
    ↓
[A2 处理] → 完成？
    ↓ 是
[触发 A3] → A2 → A3
    ↓
... (以此类推)
    ↓
[A9 离场] → 完成？
    ↓ 是
[触发 A7] → A9 → A7
    ↓
[A7 实践记录] → 完成？
    ↓ 是
[触发 A8] → A7 → A8
    ↓
[A8 理论验证] → 完成
    ↓
[理论修正] → A8 → A2/A3
    ↓
[下一轮执行] → A0 信号
```

---

### 2. 情报环触发机制

#### A6 中枢 5 级放射触发

| 级别 | 触发条件 | 目标模块 | 动作 | 消息类型 |
|------|----------|----------|------|----------|
| **L0 致命** | `risk_score >= 0.9` | A9 | 立即离场 | EVENT |
| **L1 高** | `risk_score >= 0.7` | A4 | 重新验证 | REQUEST |
| **L1.5 变** | `regime_change == true` | A2 | 增量更新 | REQUEST |
| **L2 中** | `risk_score >= 0.5` | 观察 | 记录日志 | NOTIFICATION |
| **L3 背离** | `theory_practice_score < 0.7` | A1+A3 | 重启调研 | EVENT |

#### 触发流程

```
A6 每小时运行
    ↓
[监控市场状态]
    ↓
[5级评估]
    ↓
┌─────────────────────────────────────────┐
│ L0 致命？ → 是 → 触发 A9 (离场)      │
│ L1 高？   → 是 → 触发 A4 (验证)      │
│ L1.5 变？ → 是 → 触发 A2 (更新)     │
│ L2 中？   → 是 → 记录观察             │
│ L3 背离？ → 是 → 触发 A1+A3 (重启)  │
└─────────────────────────────────────────┘
    ↓
[执行相应动作]
    ↓
[通知相关模块]
```

---

### 3. 治理环触发机制

#### 触发类型

| 触发类型 | 触发源 | 目标模块 | 条件 |
|----------|----------|----------|------|
| **事件触发** | A9 | A7 | 离场完成 |
| **时间触发** | 定时器 | A8 | 每日 14:00 |
| **事件触发** | A8 | A2/A3 | 理论修正 |

#### 理论闭环触发流程

```
A7 实践记录
    ↓
[记录执行过程]
    ↓
[提炼经验教训]
    ↓
[触发 A8] → A7 → A8
    ↓
[A8 理论验证]
    ↓
[知行合一检查]
    ↓
[批判性分析]
    ↓
[生成理论修正建议]
    ↓
[触发 A2/A3] → A8 → A2/A3
    ↓
[A2/A3 理论修正]
    ↓
[更新理论模型]
    ↓
[优化策略逻辑]
    ↓
[下一轮实践] → A7
```

---

## 消息格式定义

### 1. 执行环消息格式

#### A1 → A2: 调研报告消息

```json
{
  "header": {
    "message_id": "msg_a1_a2_20260511_1030_001",
    "timestamp": "2026-05-11T10:30:00+08:00",
    "version": "2.0",
    "source": "A1",
    "target": "A2",
    "type": "REQUEST",
    "priority": "HIGH",
    "correlation_id": "sig_20260511_1010",
    "trace_id": "trace_20260511_1010",
    "loop_type": "execution",
    "timeout_ms": 60000
  },
  "payload": {
    "research_id": "a1_research_20260511_1030",
    "signal_id": "sig_20260511_1010",
    "research_data": {
      "market_analysis": { /* ... */ },
      "historical_cases": { /* ... */ },
      "macro_environment": { /* ... */ },
      "sentiment_analysis": { /* ... */ }
    },
    "conclusions": {
      "triangular_assessment": "BULLISH",
      "signal_sufficiency": 0.85,
      "action_pressure": "HIGH"
    },
    "artifact_path": "artifacts/trading/a1_research/a1_research_20260511_1030.md"
  }
}
```

#### A2 → A3: 分析报告消息

```json
{
  "header": {
    "message_id": "msg_a2_a3_20260511_1050_001",
    "timestamp": "2026-05-11T10:50:00+08:00",
    "version": "2.0",
    "source": "A2",
    "target": "A3",
    "type": "REQUEST",
    "priority": "HIGH",
    "correlation_id": "sig_20260511_1010",
    "trace_id": "trace_20260511_1010",
    "loop_type": "execution",
    "timeout_ms": 60000
  },
  "payload": {
    "analysis_id": "a2_analysis_20260511_1050",
    "research_id": "a1_research_20260511_1030",
    "analysis_data": {
      "contradiction_analysis": { /* ... */ },
      "regime_classification": "TREND_STRONG",
      "path_of_least_resistance": "UP",
      "clarity": "CLEAR"
    },
    "artifact_path": "artifacts/trading/a2_analysis/a2_analysis_20260511_1050.md"
  }
}
```

#### A6 → A9: L0 致命警报消息 (情报环 → 执行环)

```json
{
  "header": {
    "message_id": "msg_a6_a9_20260511_1300_001",
    "timestamp": "2026-05-11T13:00:00+08:00",
    "version": "2.0",
    "source": "A6",
    "target": "A9",
    "type": "EVENT",
    "priority": "CRITICAL",
    "correlation_id": null,
    "trace_id": "trace_a6_20260511_1300",
    "loop_type": "intelligence",
    "timeout_ms": 0
  },
  "payload": {
    "alert_id": "alert_20260511_1300",
    "alert_level": "L0",
    "alert_type": "RISK_EVENT",
    "alert_data": {
      "risk_score": 0.95,
      "event_type": "BLACK_SWAN",
      "description": "黑天鹅事件，立即离场"
    },
    "action_required": true,
    "target_module": "A9",
    "action": "IMMEDIATE_EXIT"
  }
}
```

#### A7 → A8: 实践记录消息 (治理环)

```json
{
  "header": {
    "message_id": "msg_a7_a8_20260511_1400_001",
    "timestamp": "2026-05-11T14:00:00+08:00",
    "version": "2.0",
    "source": "A7",
    "target": "A8",
    "type": "REQUEST",
    "priority": "MEDIUM",
    "correlation_id": "sig_20260511_1010",
    "trace_id": "trace_20260511_1010",
    "loop_type": "governance",
    "timeout_ms": 300000
  },
  "payload": {
    "practice_id": "a7_practice_20260511_1400",
    "execution_id": "a5_execution_20260511_1200",
    "practice_data": {
      "decision": "BUY BTC/USDT @ $96,500",
      "theory_basis": "a3_strategy_20260511_1100",
      "execution_result": "SUCCESS, profit +5%",
      "lessons_learned": "入场时机可优化"
    },
    "artifact_path": "artifacts/trading/a7_practice/a7_practice_20260511_1400.md"
  }
}
```

---

## 状态机与转换

### 全局状态机 (三大闭环)

```
                ┌───────────┐
                │   IDLE    │  (空闲)
                └─────┬─────┘
                      │ A0 信号触发
                      ▼
                ┌───────────┐
                │  SIGNAL   │  (信号检测) - A0
                └─────┬─────┘
                      │ A0 完成
                      ▼
                ┌───────────┐
                │ RESEARCH  │  (调研中) - A1
                └─────┬─────┘
                      │ A1 完成
                      ▼
                ┌───────────┐
                │ ANALYZING │  (分析中) - A2
                └─────┬─────┘
                      │ A2 完成
                      ▼
                ┌───────────┐
                │ STRATEGIZ │  (策略制定) - A3
                └─────┬─────┘
                      │ A3 完成
                      ▼
                ┌───────────┐
                │ VALIDATING│  (验证中) - A4
                └─────┬─────┘
                      │ A4 完成
                      ▼
                ┌───────────┐
                │ EXECUTING │  (执行中) - A5
                └─────┬─────┘
                      │ A5 完成
                      ▼
                ┌───────────┐
                │ MONITORING │  (监控中) - A6
                └─────┬─────┘
                      │ A6 警报 (L0-L3)
                      ▼
                ┌───────────┐
                │  ALERT    │  (警报处理)
                └─────┬─────┘
                      │ 处理完成
                      ▼
                ┌───────────┐
                │   EXIT    │  (已离场) - A9
                └─────┬─────┘
                      │ A9 完成
                      ▼
                ┌───────────┐
                │ PRACTICE  │  (实践记录) - A7
                └─────┬─────┘
                      │ A7 完成
                      ▼
                ┌───────────┐
                │VERIFICATION│  (理论验证) - A8
                └─────┬─────┘
                      │ A8 完成
                      ▼
                ┌───────────┐
                │   IDLE    │  (回到空闲)
                └───────────┘
```

---

## 处罚与重试机制

### 1. 处罚机制 (Penalty Mechanism)

#### 处罚规则

| 违规行为 | 处罚类型 | 处罚力度 | 恢复条件 | 适用闭环 |
|----------|----------|----------|----------|----------|
| **超时未响应** | 警告 | -10 分 | 下次成功执行 | 执行环、治理环 |
| **消息格式错误** | 警告 | -5 分 | 下次格式正确 | 所有闭环 |
| **处理失败** | 扣分 | -20 分 | 下次成功执行 | 所有闭环 |
| **连续失败 3 次** | 降级 | 优先级降低 | 连续成功 5 次 | 所有闭环 |
| **恶意消息** | 封禁 | 模块禁用 | 人工审核 | 所有闭环 |
| **理论背离** | 警告 | -15 分 | 理论修正 | 治理环 |

---

## 实现示例

### 1. 执行环通信实现 (HTTP REST API)

#### A1 调研处理器 (接收方)

```python
from flask import Flask, request, jsonify
from typing import Dict
import json

app = Flask(__name__)

class A1ResearchProcessor:
    def __init__(self):
        self.state = "IDLE"
        self.current_task = None
    
    def process_signal(self, message: Dict) -> Dict:
        """处理 A0 信号"""
        # 验证消息格式
        if not self.validate_message(message):
            return {"status": "ERROR", "reason": "Invalid message format"}
        
        # 更新状态
        self.state = "RECEIVED"
        
        # 开始处理
        self.state = "PROCESSING"
        try:
            # 执行调研逻辑
            research_result = self.conduct_research(message["payload"])
            
            # 更新状态
            self.state = "COMPLETED"
            
            # 触发 A2
            self.trigger_a2(research_result)
            
            return {"status": "SUCCESS", "data": research_result}
            
        except Exception as e:
            self.state = "ERROR"
            return {"status": "ERROR", "reason": str(e)}
    
    def validate_message(self, message: Dict) -> bool:
        """验证消息格式"""
        required_fields = ["header", "payload"]
        for field in required_fields:
            if field not in message:
                return False
        
        required_header_fields = ["message_id", "source", "target", "type", "loop_type"]
        for field in required_header_fields:
            if field not in message["header"]:
                return False
        
        return True
    
    def conduct_research(self, signal_data: Dict) -> Dict:
        """执行调研逻辑（示例）"""
        # 这里实现 A1 的调研逻辑
        return {
            "research_id": "a1_research_20260511_1030",
            "signal_id": signal_data["signal_id"],
            "conclusions": {
                "triangular_assessment": "BULLISH",
                "signal_sufficiency": 0.85
            }
        }
    
    def trigger_a2(self, research_result: Dict):
        """触发 A2"""
        # 构造 A1 → A2 消息
        message = {
            "header": {
                "message_id": f"msg_a1_a2_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
                "source": "A1",
                "target": "A2",
                "type": "REQUEST",
                "loop_type": "execution"
            },
            "payload": research_result
        }
        
        # 发送到 A2
        # requests.post("http://localhost:5001/a2/analysis", json=message)
        pass

processor = A1ResearchProcessor()

@app.route('/a1/signals', methods=['POST'])
def receive_signal():
    message = request.json
    result = processor.process_signal(message)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
```

---

### 2. 情报环通信实现 (消息队列 - RabbitMQ)

#### A6 警报发布者 (A6 中枢)

```python
import pika
import json
from datetime import datetime
from typing import Dict

class A6AlertPublisher:
    def __init__(self, host: str = 'localhost'):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=host)
        )
        self.channel = self.connection.channel()
        
        # 声明 Topic Exchange
        self.channel.exchange_declare(
            exchange='dream_intelligence',
            exchange_type='topic',
            durable=True
        )
    
    def publish_alert(self, alert_data: Dict, alert_level: str):
        """发布警报"""
        routing_key = f"dream.intelligence.a6.{alert_level.lower()}"
        
        message = {
            "header": {
                "message_id": f"msg_a6_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0",
                "source": "A6",
                "target": alert_data["target_module"],
                "type": "EVENT" if alert_level in ["L0", "L3"] else "REQUEST",
                "priority": "CRITICAL" if alert_level == "L0" else "HIGH",
                "loop_type": "intelligence"
            },
            "payload": alert_data
        }
        
        # 发布消息
        self.channel.basic_publish(
            exchange='dream_intelligence',
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 持久化
                content_type='application/json'
            )
        )
        
        print(f"✅ 警报已发布: {routing_key}")
    
    def close(self):
        self.connection.close()

# 使用示例
publisher = A6AlertPublisher()

# L0 致命 → A9
alert_data_l0 = {
    "alert_id": "alert_20260511_1300",
    "alert_level": "L0",
    "alert_type": "RISK_EVENT",
    "alert_data": {"risk_score": 0.95, "event_type": "BLACK_SWAN"},
    "action_required": True,
    "target_module": "A9",
    "action": "IMMEDIATE_EXIT"
}
publisher.publish_alert(alert_data_l0, "L0")

publisher.close()
```

---

## 总结

本文档定义了 Dream-MultiSkill A0-A9 系统的 **三大核心闭环架构**：

1. **执行环 (Execution Loop)** - 蓝色
   - 模块序列: A1→A2→A3→A4→A5→A9
   - 通信模式: 同步调用 (HTTP REST API)
   - 触发机制: 事件触发 + 依赖触发

2. **情报环 (Intelligence Loop)** - 琥珀色
   - A6 中枢 5 级放射驱动: L0→A9, L1→A4, L1.5→A2, L2→观察, L3→A1+A3
   - 通信模式: 异步通知 (消息队列)
   - 触发机制: 定时触发 (每小时) + 事件驱动

3. **治理环 (Governance Loop)** - 紫色
   - 理论闭环: A7→A8→A2/A3
   - 通信模式: 请求/响应 (HTTP REST API)
   - 触发机制: 事件触发 + 时间触发 (每日 14:00)

### 文档内容

1. **三大闭环架构** - 执行环、情报环、治理环
2. **通信协议规范** - 消息头、消息类型、传输协议
3. **闭环触发机制** - 各闭环的触发流程和条件
4. **消息格式定义** - 执行环、情报环、治理环的消息格式
5. **状态机与转换** - 全局状态机
6. **处罚与重试机制** - 积分系统、重试策略
7. **实现示例** - HTTP REST API、消息队列 (RabbitMQ)

---

**END OF DOCUMENT**
