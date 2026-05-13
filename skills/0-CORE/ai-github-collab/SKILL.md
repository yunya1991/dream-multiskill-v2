---
name: ai-github-collab
description: AI 参与的 GitHub 协作规范与门禁对齐技能。用于“多 AI 并行开发”“拆任务/定 scope”“生成 PR 模板”“需要 override”“门禁失败修复”等场景，强制硬规则、角色分工、分支命名、AI_COLLAB 契约、override 审计与失败修复剧本。
---

# 多 AI GitHub 协作 SKILL

目标：让“多人/多 AI 并行改仓库”仍然可控、可审计、可回滚；以 fail-closed（失败即阻断）为默认安全策略。  
定位：这是“协作卫生层 + 元信息契约层”，不替代主干合并门禁；需与 `safe-main-merge`、`code-review-merge-assistant` 共存。

## 触发意图

- 多 AI/多人并行改同一仓库，需要“分工 + scope + 反污染 + 审计”
- 需要为 PR 生成机器可读契约（AI_COLLAB 区块）
- 需要制定分支命名、PR 粒度、依赖声明、冲突集成策略
- 门禁失败（缺 AI_COLLAB / scope 外改动 / forbidden path / 风险未提供测试 / scope 重叠等）需要修复

## 硬规则（Hard Rules）

1. 禁止直推 `main`；任何变更必须通过 PR。
2. 一个 PR 只做一件事；禁止把多个不相关主题堆叠到同一个 PR。
3. PR 必须包含 `AI_COLLAB` 机器可读区块；缺失或非法视为失败（MISSING/INVALID）。
4. 变更文件必须全部落在 `AI_COLLAB.scope` 内；否则失败（OUT_OF_SCOPE_CHANGE）。
5. 命中 forbidden 路径/文件（如 `.workbuddy/**`、`artifacts/**`、`.env*`、`*.log`、大二进制等）直接失败（FORBIDDEN_PATH/LARGE_FILE_BLOCKED）。
6. `risk=medium|high` 必须提供非空 `tests`（RISK_REQUIRES_TESTS）；并在本地跑通后再 push。
7. 不允许隐式放宽规则：PR 只能更严格，不能更宽松；例外只能走 override 机制且必须可审计。

## 角色模型（Role Model）

- 编排者（Coordinator）
  - 拆任务、分配 scope、定义风险、制定验证方式、处理冲突与集成 PR
  - 唯一允许发起 override（加 label + 书面说明）的角色
- 执行者（Worker）
  - 只实现单一任务；严格在 scope 内改动；提供验证证据；不自行决定 override
- 守卫（CI Guard）
  - 解析 PR body 的 `AI_COLLAB`，检查 scope/forbidden/风险测试/重叠等，fail-closed 阻断合并

## 分支命名（Branch Naming）

默认模式：

- 执行者分支：`ai/<topic>/<agent>/<ticket>`
- 集成分支（仅编排者）：`ai/integration/<topic>/<ticket>`

规则：

- 一个执行者分支只对应一个 PR（1 branch ↔ 1 PR）。
- 集成 PR 只用于冲突解决/多 PR 集成，不做功能开发堆叠。

## PR 必填：AI_COLLAB 模板（复制到 PR body）

要求：推荐使用 fenced `yaml` 代码块；`scope` 必填且非空；`risk != low` 时 `tests` 必填。

```yaml
AI_COLLAB:
  version: 1
  agent: A2
  role: worker  # worker | coordinator
  topic: demo
  ticket: T123
  base: main
  scope:
    - "scripts/**"
    - "tests/test_ci_*"
  forbidden:
    - ".workbuddy/**"
    - "artifacts/**"
  tests:
    - "python -m pytest -q tests/test_ci_ai_collab_guard.py"
  risk: low  # low | medium | high
  rollback:
    strategy: revert
    notes: "Revert squash commit of this PR"
  deps:
    prs: []
```

填写口径：

- `topic/ticket`：用于把一组 PR 归并到同一协作主题。
- `scope`：用 glob 表达“允许改动的路径集合”，要尽可能窄。
- `forbidden`：可写可不写；写了只能更严格（收紧），不能放宽仓库策略。
- `tests`：写你实际执行过的命令（CI 不会自动执行 PR body 中任意命令）。
- `rollback`：必须可执行、可描述（至少说明 revert 策略）。

## Override 机制（必须审计）

只允许编排者使用以下 labels（统一前缀 `ai-collab/*`），并且必须在 PR 评论中说明：原因、影响范围、有效期/一次性、替代方案与回滚计划。

- `ai-collab/override-scope`：允许临时放宽 scope（需要明确列出被放宽的文件/原因）
- `ai-collab/allow-generated`：允许提交生成物（必须说明为何不可重建或为何需要纳入版本控制）
- `ai-collab/allow-large-files`：允许大文件（必须说明大小/来源/必要性）
- `ai-collab/dependency-chain`：允许依赖链（必须在 `deps.prs` 明确列出依赖 PR）

编排者审计评论模板：

```text
AI-COLLAB OVERRIDE
- label: ai-collab/xxxx
- reason: <为什么必须例外>
- scope impact: <哪些文件/路径受影响>
- duration: <一次性/直到某日期/直到某PR合并>
- mitigations: <如何降低风险（加测/加审/限制发布等）>
- rollback: <如何回滚>
```

## 门禁失败修复指引（Fail → Fix → Recheck）

通用步骤：

1. 查看 PR body 与变更文件列表（网页或 `gh pr view`）
2. 对照失败 reason code 修复
3. push 到同一分支触发重新检查；必要时编辑 PR body 触发 `edited`

常见失败与修复动作：

- `MISSING_AI_COLLAB`：在 PR body 补上 fenced `yaml` 的 `AI_COLLAB:` 区块
- `INVALID_AI_COLLAB`：修正 YAML 缩进/字段类型；确保 `AI_COLLAB.scope` 为非空 list
- `OUT_OF_SCOPE_CHANGE`：
  - 优先拆 PR 或还原超范围文件
  - 或精确调整 scope 覆盖本 PR
  - 仅编排者可用 `ai-collab/override-scope`，并写审计评论
- `FORBIDDEN_PATH`：删除污染文件/目录；必要时补充 `.gitignore`（不要把污染留在仓库里）
- `LARGE_FILE_BLOCKED`：替换为更小的文本/配置或外链；确需提交由编排者 `ai-collab/allow-large-files` + 审计
- `RISK_REQUIRES_TESTS`：在 `AI_COLLAB.tests` 补上实际跑过的命令，并在本地跑通后再 push
- `SCOPE_OVERLAP_REQUIRES_OVERRIDE`：联系编排者统一调整各 PR scope；或由编排者 override 并说明原因

## 输出标准

- 分支名（head/base）与 PR 链接
- AI_COLLAB 区块（最终版）+ scope 说明
- 风险等级（risk）+ 验证证据（tests 及结果摘要）
- 如使用 override：label + 审计评论要点 + 回滚策略

