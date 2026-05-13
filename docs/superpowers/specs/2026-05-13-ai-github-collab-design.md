# 多 AI GitHub 协作 SKILL 设计（编排者 + 执行者工作流）
日期：2026-05-13  
状态：草案（设计）  
范围：面向多 AI 并行开发的通用 GitHub 协作规范与门禁设计；以 `dream-multiskill-v2` 作为参考落地点

## 1. 问题定义

多 AI 并行在 GitHub 仓库中协作时，容易出现系统性失败：

- 误污染 `main`（直推、错误 base、危险操作）；
- PR scope 混乱（把无关文件、运行产物、临时目录混进来）；
- 多 PR 范围重叠导致频繁冲突，且缺少协调机制；
- 验证不一致（不跑测试、测试口径不同、口头承诺无证据）；
- 历史难追溯（多 AI 反复 rebase/amend 导致审计困难）。

目标：设计一个协作 SKILL，强制采用确定性 GitHub 工作流，并用 fail-closed 的 CI 门禁阻断违规行为，使多 AI 协作保持安全、可审阅、可合并、可回滚。

## 2. 目标与非目标

### 目标

- 通过流程 + 自动化共同保护 `main`（禁止直推、必须 PR 合并）。
- 提供适用于多 AI 并行的“编排者 + 执行者”协作模型。
- 让 PR scope 可机器校验，减少误混文件与跨任务碰撞。
- 使用 fail-closed CI 门禁：缺元信息或策略违规直接阻断合并。
- 保证可审计：每个 PR 都有结构化元信息、验证命令、回滚提示。
- 具备可迁移性：通过配置文件适配不同仓库，而非重写核心逻辑。

### 非目标

- 不替代仓库已有的合并门禁（例如 safe-main-merge 等）。
- 不自动批准 PR，也不绕过必须的 checks / review。
- 不自动解决所有冲突（冲突解决仍归编排者负责）。
- 不对受保护分支执行破坏性自动化操作。

## 3. 运行模型（编排者 + 执行者）

### 3.1 角色

- 编排者（Coordinator）
  - 拆解任务并为每个任务分配独立 PR scope；
  - 规划集成顺序并解决跨 PR 冲突；
  - 负责 override 决策与升级处理。
- 执行者（Worker）
  - 在独立分支内完成单一任务且只能改动分配的 scope；
  - 在 PR 元信息中提供验证证据；
  - 永不直接触碰 `main`。

### 3.2 协作载体（只通过 GitHub）

协作通过以下方式表达：

- 分支命名规范；
- PR 标题 + body（含机器可读 `AI_COLLAB` 区块）；
- 用于 override / 升级的标签；
- CI 产物（artifacts）记录门禁决策与原因。

## 4. 分支与 PR 约定（硬规则）

### 4.1 分支命名

默认模式：

- 执行者分支：`ai/<topic>/<agent>/<ticket>`
- 集成分支（仅编排者）：`ai/integration/<topic>/<ticket>`

规则：

- 一个执行者分支只能对应一个 PR；
- 集成 PR 仅用于冲突解决或多 PR 集成，不做功能开发堆叠。

### 4.2 PR 粒度

- 一个 PR 只做一件事。
- PR 禁止包含生成物与本地运行状态目录。
- PR 应能独立合并到 `main`；如必须依赖其他 PR，需要显式声明依赖关系。

## 5. 机器可读 PR 契约（AI_COLLAB 区块）

每个 PR 必须在 body 中包含 YAML 区块：

```yaml
AI_COLLAB:
  version: 1
  agent: A2
  role: worker  # worker | coordinator
  topic: qmm-v5
  ticket: T123
  base: main
  scope:
    - "scripts/memory_l4/qmm_v5/**"
    - "tests/test_qmm_v5_*"
  forbidden:
    - ".workbuddy/**"
    - "artifacts/**"
  tests:
    - "python -m pytest -q tests/test_qmm_v5_prototype.py"
  risk: low  # low | medium | high
  rollback:
    strategy: revert
    notes: "Revert squash commit of this PR"
  deps:
    prs: []
```

契约要求：

- `scope` 必填且不能为空。
- scope 必须足够窄（可由策略配置最大 patterns 数、最大变更文件数）。
- `risk != low` 时 `tests` 必须非空；建议所有 PR 都填。
- `forbidden` 默认来自仓库策略；PR 只能进一步收紧，不能放宽。

Fail-closed：缺少区块或格式非法，CI 必须失败并阻断合并。

## 6. 策略执行（CI 门禁）

### 6.1 基础门禁规则

1. 分支安全
   - PR head 分支不得为 `main`。
   - PR base 分支必须为 `main`（或策略允许的 base）。
2. Scope 校验
   - 所有变更文件必须命中 `scope` patterns；
   - 任一文件命中 forbidden patterns 直接失败。
3. 反污染
   - 默认禁止 `.workbuddy/**`、`artifacts/**`、`*.log`、`*.tmp`、`.env*`、大二进制等；
   - 机密扫描：基于规则的启发式检测 + 依赖 GitHub Secret Scanning（存在则双保险）。
4. 验证证据
   - `risk=medium|high` 必须提供非空 `tests`；
   - CI 记录宣称的测试命令（CI 不自动执行 PR body 里的任意命令）。
5. 并发保护
   - 若多个 open PR scope 重叠（可配置规则），必须有编排者 override 标签才允许继续。

### 6.2 Override 标签（显式且可审计）

所有 override 标签统一使用 `ai-collab/*` 前缀：

- `ai-collab/override-scope`（仅编排者）
- `ai-collab/allow-generated`（必须说明原因）
- `ai-collab/allow-large-files`（必须说明原因）
- `ai-collab/dependency-chain`（允许 PR 依赖链）

Override 必须配套编排者评论，说明具体例外原因与影响范围。

### 6.3 审计产物

每次 CI 运行输出：

- `artifacts/ai_collab/guard-<run_id>.json`
- `artifacts/ai_collab/summary-<run_id>.md`

产物内容包括：

- PR 编号、head SHA、base SHA
- 解析后的 AI_COLLAB 区块
- 变更文件列表与分类（in-scope / out-of-scope / forbidden）
- scope 重叠检测结果
- 最终结论：pass/fail + reason codes

## 7. 仓库改动（参考落地）

### 7.1 新增 Skill

路径：

- `skills/0-CORE/ai-github-collab/SKILL.md`

Skill 责任：

- 指导编排者生成 PR scope 与任务拆分计划；
- 在交互流程中强制“禁止污染 main”；
- 指导执行者补齐 `AI_COLLAB` 元信息；
- 提供标准化失败处理剧本（修复路径、重新触发门禁）。

### 7.2 新增策略文件（可迁移配置）

路径：

- `.github/ai-collab-policy.yml`

包含：

- 允许的 base branches
- 禁止的 globs
- scope 最大 patterns 数、最大变更文件数、最大文件体积
- scope 重叠检测模式
- required checks 清单（可选，用于与仓库既有门禁对齐）

### 7.3 新增 CI 守卫脚本

路径：

- `scripts/ci/ai_collab_guard.py`

输入：

- `--repo`
- `--pr-number`
- `--policy-file`
- `--dry-run`

职责：

- 拉取 PR 元信息与 diff 文件列表（GitHub API）；
- 从 PR body 解析 `AI_COLLAB`；
- 加载策略文件并评估规则；
- 输出审计产物，并以稳定错误码退出（fail-closed）。

### 7.4 新增 GitHub Workflow

路径：

- `.github/workflows/ai-collab-pr-guard.yml`

触发：

- `pull_request`（opened, synchronize, edited, labeled）

权限（最小可用）：

- `contents: read`
- `pull-requests: read`

Artifacts:

- upload guard artifacts for each run.

## 8. 失败语义（Fail-Closed）

所有违规必须阻断合并，并返回确定性 reason codes：

- `MISSING_AI_COLLAB`
- `INVALID_AI_COLLAB`
- `OUT_OF_SCOPE_CHANGE`
- `FORBIDDEN_PATH`
- `LARGE_FILE_BLOCKED`
- `SCOPE_OVERLAP_REQUIRES_OVERRIDE`
- `RISK_REQUIRES_TESTS`

PR 作者通过修改 PR body 与/或分支内容修复，然后 push 触发重新检查。

## 9. 与既有合并流程的关系

本设计必须与以下机制共存：

- 仓库特定的 safe main merge 门禁（如 safe-main-merge 工作流）；
- 既有 review policy 与 required checks；
- 既有分支生命周期治理（branch lifecycle automation）。

AI-collab gate 不替代合并门禁；它是协作卫生与安全层，用于避免多 AI 并行带来的系统性污染与混乱。

## 10. 推进计划

阶段 0（观察）：

- workflow 以 `dry-run` 模式运行：仅输出审计产物与提示，不阻断合并。

阶段 1（强制元信息 + 反污染）：

- 缺少 AI_COLLAB 或触碰 forbidden paths 的 PR 直接失败。

阶段 2（强制 scope + 重叠策略）：

- 启用严格 scope 校验与 scope 重叠检测。

阶段 3（调参）：

- 调整阈值、补充仓库特定 patterns、细化 reason codes。

## 11. 测试策略

单元测试：

- AI_COLLAB 解析正确性
- glob 匹配与 scope 校验
- forbidden path 检测
- 基于合成 PR 集的 scope 重叠检测
- 稳定错误码与审计产物格式

集成测试（可选）：

- dry-run workflow 在样例 PR 事件 payload 上可运行
- 与既有 required checks 配置兼容
