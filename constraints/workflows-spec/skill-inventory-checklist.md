# SKILL 全量清单（用于迁移对齐）

- 生成时间：`2026-05-10T16:57:23Z`
- 源基线：`dream-trading-automation@feature/add-skills`
- 目标基线：`dream-multiskill-v2`（本地）
- 外部参考：CodeBuddy 分享页显示总量 `88`（User 86 + Project 2），用于规模校验。

## 1. 数量总览

- 源仓 `SKILL.md` 数量（排除 `.workbuddy`）：`47`
- 目标仓 `SKILL.md` 数量：`3`
- 迁移缺口（按文件数）：`44`

## 2. 源仓分层清单（完整）

### 0-CORE（8）

- `0-CORE/artifact-alignment-manager/SKILL.md`
- `0-CORE/dream-constitution/SKILL.md`
- `0-CORE/dream-governance-manager/SKILL.md`
- `0-CORE/dream-knowledge/SKILL.md`
- `0-CORE/learning-episode-writer/SKILL.md`
- `0-CORE/learning-lesson-distiller/SKILL.md`
- `0-CORE/learning-proposal-generator/SKILL.md`
- `0-CORE/memory-manager/SKILL.md`

### 1-TRADE（16）

- `1-TRADE/A7-practice-theory/SKILL.md`
- `1-TRADE/A8-theory-practice-verification/SKILL.md`
- `1-TRADE/dream-contradiction-theory/SKILL.md`
- `1-TRADE/dream-execution-cost-model/SKILL.md`
- `1-TRADE/dream-exit-skill-v2/SKILL.md`
- `1-TRADE/dream-first-principles/SKILL.md`
- `1-TRADE/dream-intelligence-monitor/SKILL.md`
- `1-TRADE/dream-pretrade-gatekeeper/SKILL.md`
- `1-TRADE/dream-regime-detector/SKILL.md`
- `1-TRADE/dream-risk-position-sizing/SKILL.md`
- `1-TRADE/dream-signal-scoring-spec/SKILL.md`
- `1-TRADE/dream-strategy-designer/SKILL.md`
- `1-TRADE/dream-strategy-parser/SKILL.md`
- `1-TRADE/dream-strategy-research/SKILL.md`
- `1-TRADE/dream-tactical-executor/SKILL.md`
- `1-TRADE/dream-tactical-validator/SKILL.md`

### 2-INTELLIGENCE（7）

- `2-INTELLIGENCE/dream-archive-center/SKILL.md`
- `2-INTELLIGENCE/dream-bailian-integration/SKILL.md`
- `2-INTELLIGENCE/dream-data-analysis/SKILL.md`
- `2-INTELLIGENCE/dream-intelligence-analysis/SKILL.md`
- `2-INTELLIGENCE/dream-knowledge/SKILL.md`
- `2-INTELLIGENCE/dream-oneirology/SKILL.md`
- `2-INTELLIGENCE/master-seminar/SKILL.md`

### 3-SUPPORT（9）

- `3-SUPPORT/ai-trading-compliance/SKILL.md`
- `3-SUPPORT/auto-repair/SKILL.md`
- `3-SUPPORT/boss-secretary/SKILL.md`
- `3-SUPPORT/dream-cost-control/SKILL.md`
- `3-SUPPORT/dream-hr-recruitment/SKILL.md`
- `3-SUPPORT/dream-operation-director/SKILL.md`
- `3-SUPPORT/dream-performance-review/SKILL.md`
- `3-SUPPORT/dream-product-hub-maintenance/SKILL.md`
- `3-SUPPORT/resource-efficiency-analyst/SKILL.md`

### 4-GENERIC（7）

- `4-GENERIC/find-skills/SKILL.md`
- `4-GENERIC/github/SKILL.md`
- `4-GENERIC/markdown-convert/SKILL.md`
- `4-GENERIC/ontology/SKILL.md`
- `4-GENERIC/skill-creator/SKILL.md`
- `4-GENERIC/skill-creator/skill-creator/SKILL.md`
- `4-GENERIC/tavily/SKILL.md`

## 3. 目标仓现状（本地专项检查）

- `skills/0-CORE/architecture-sync-guard/SKILL.md`
- `skills/0-CORE/code-review-merge-assistant/SKILL.md`
- `skills/0-CORE/safe-main-merge/SKILL.md`

## 4. A0-A9 关键技能迁移白名单（第一批）

- `A0`: `1-TRADE/dream-contradiction-theory/SKILL.md`
- `A1`: `1-TRADE/dream-strategy-research/SKILL.md`
- `A2`: `1-TRADE/dream-first-principles/SKILL.md`
- `A3`: `1-TRADE/dream-strategy-designer/SKILL.md`, `1-TRADE/dream-strategy-parser/SKILL.md`
- `A4`: `1-TRADE/dream-tactical-validator/SKILL.md`, `1-TRADE/dream-pretrade-gatekeeper/SKILL.md`
- `A5`: `1-TRADE/dream-tactical-executor/SKILL.md`
- `A6`: `1-TRADE/dream-intelligence-monitor/SKILL.md`, `1-TRADE/dream-signal-scoring-spec/SKILL.md`, `1-TRADE/dream-regime-detector/SKILL.md`
- `A7`: `1-TRADE/A7-practice-theory/SKILL.md`
- `A8`: `1-TRADE/A8-theory-practice-verification/SKILL.md`
- `A9`: `1-TRADE/dream-exit-skill-v2/SKILL.md`

## 5. 迁移建议

- 先迁移 `1-TRADE` 的 A0-A9 对应技能，再补齐 `0-CORE` 记忆/治理依赖技能。
- 每个技能目录迁移时必须携带：`SKILL.md`、`scripts/`、`templates/`、`gates/`、`test_cases/`（如存在）。
- 迁移完成后，在 `constraints/workflows-spec/` 同步更新链路与技能清单版本。
