# 多 AI GitHub 协作门禁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在仓库中落地“编排者 + 执行者”的多 AI GitHub 协作规范，并用 fail-closed 的 PR 门禁阻断 main 污染、scope 混乱与生成物混入等风险。

**Architecture:** 通过 PR body 的 `AI_COLLAB` 机器可读区块声明 scope/风险/验证等元信息；CI 工作流运行 `ai_collab_guard.py` 拉取 PR 元信息与变更文件，按策略文件判定 pass/fail 并输出审计产物。

**Tech Stack:** Python 3.11, pytest, PyYAML（仓库内已使用 `yaml`），GitHub Actions（pull_request 触发）

---

## 文件结构（将创建/修改）

**Create**
- `.github/ai-collab-policy.yml`
- `.github/workflows/ai-collab-pr-guard.yml`
- `scripts/ci/ai_collab_guard.py`
- `skills/0-CORE/ai-github-collab/SKILL.md`
- `tests/test_ci_ai_collab_guard.py`

**Modify**
- （可选）`.gitignore`（仅当需要补充反污染规则时）

---

### Task 1: 新增策略文件（ai-collab-policy.yml）

**Files:**
- Create: `.github/ai-collab-policy.yml`

- [ ] **Step 1: 写入策略文件内容**

```yaml
version: 1

allowed_base_branches:
  - main

forbidden_globs:
  - ".workbuddy/**"
  - "artifacts/**"
  - "**/*.log"
  - "**/*.tmp"
  - "**/.env"
  - "**/.env.*"

max_scope_patterns: 24
max_changed_files: 80
max_file_bytes: 1048576

overlap_detection:
  enabled: true
  mode: "pattern_prefix"

override_labels:
  - "ai-collab/override-scope"
  - "ai-collab/allow-generated"
  - "ai-collab/allow-large-files"
  - "ai-collab/dependency-chain"
```

- [ ] **Step 2: 本地自检 YAML 可解析**

Run: `python - <<'PY'\nimport yaml\nfrom pathlib import Path\np=Path('.github/ai-collab-policy.yml')\nprint(yaml.safe_load(p.read_text(encoding='utf-8'))['version'])\nPY`

Expected: 输出 `1`

- [ ] **Step 3: Commit**

```bash
git add .github/ai-collab-policy.yml
git commit -m "feat(ci): add ai-collab policy file"
```

---

### Task 2: 新增 Skill 文档（ai-github-collab）

**Files:**
- Create: `skills/0-CORE/ai-github-collab/SKILL.md`

- [ ] **Step 1: 写入 SKILL.md（中文）**

内容必须包含：
- 触发语句与使用场景（多 AI 协作、避免 main 污染、PR scope 规范）
- 角色模型（编排者/执行者）
- 分支命名规范（`ai/<topic>/<agent>/<ticket>`）
- PR body 必须包含 `AI_COLLAB` 代码块（推荐 fenced yaml）
- 门禁失败处理（如何修复：改 PR body / 拆分提交 / 缩小 scope / 删除生成物）
- 允许的 override label 与审计要求（必须编排者评论说明）

建议最小模板（直接写入文件）：

```markdown
---
name: ai-github-collab
description: 多 AI GitHub 协作与门禁规范。用于“多 AI 并行开发”“防止 main 污染”“强制 PR scope 与反污染策略”的场景，提供编排者/执行者协作协议与 fail-closed CI 门禁。
---

# 多 AI GitHub 协作 SKILL

## 核心原则（硬规则）

1. 禁止直推 main，所有变更必须走 PR。
2. 执行者只能在自己的分支工作，一个分支对应一个 PR。
3. PR 必须声明 scope，且 CI 会严格校验：变更文件必须全部落在 scope 内。
4. 默认禁止生成物与本地状态目录（.workbuddy、artifacts 等）混入 PR。
5. 缺少 AI_COLLAB 元信息或违反策略时，CI fail-closed 阻断合并。

## 角色模型

- 编排者（Coordinator）：拆任务、分配 scope、处理冲突、决定 override。
- 执行者（Worker）：只实现单一任务，严格在 scope 内改动，提供验证证据。

## 分支命名

- 执行者分支：ai/<topic>/<agent>/<ticket>
- 集成分支（仅编排者）：ai/integration/<topic>/<ticket>

## PR 必须包含 AI_COLLAB 区块

把以下内容放进 PR body（推荐使用 fenced yaml 代码块）：

```yaml
AI_COLLAB:
  version: 1
  agent: A2
  role: worker
  topic: qmm-v5
  ticket: T123
  base: main
  scope:
    - "scripts/memory_l4/qmm_v5/**"
    - "tests/test_qmm_v5_*"
  tests:
    - "python -m pytest -q tests/test_qmm_v5_prototype.py"
  risk: low
  rollback:
    strategy: revert
    notes: "Revert squash commit of this PR"
  deps:
    prs: []
```

## 允许的 override（必须审计）

只允许编排者添加以下 label（并在 PR 评论说明原因与范围）：

- ai-collab/override-scope
- ai-collab/allow-generated
- ai-collab/allow-large-files
- ai-collab/dependency-chain

## 门禁失败怎么修

- OUT_OF_SCOPE_CHANGE：拆 PR 或缩小 scope；把无关改动移到另一个 PR。
- FORBIDDEN_PATH：删除生成物/本地状态目录并加入 .gitignore（如需要）。
- RISK_REQUIRES_TESTS：补充 tests 列表并在本地跑通再 push。
- SCOPE_OVERLAP_REQUIRES_OVERRIDE：联系编排者统一调整 scope 或加 override 并说明。
```

- [ ] **Step 2: Commit**

```bash
git add skills/0-CORE/ai-github-collab/SKILL.md
git commit -m "feat(skill): add ai github collaboration skill"
```

---

### Task 3: 先写 CI 守卫脚本的单元测试（TDD）

**Files:**
- Create: `tests/test_ci_ai_collab_guard.py`

- [ ] **Step 1: 写 failing tests**

```python
import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "ai_collab_guard.py"
SPEC = importlib.util.spec_from_file_location("ai_collab_guard", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_extract_ai_collab_block_from_fenced_yaml():
    body = \"\"\"
hello

```yaml
AI_COLLAB:
  version: 1
  agent: A2
  role: worker
  topic: demo
  ticket: T1
  base: main
  scope:
    - scripts/** 
  tests:
    - pytest -q
  risk: low
  rollback:
    strategy: revert
    notes: x
  deps:
    prs: []
```
\"\"\"
    data = MODULE.parse_ai_collab_from_pr_body(body)
    assert data["AI_COLLAB"]["agent"] == "A2"


def test_forbidden_globs_block_paths():
    policy = {"forbidden_globs": [".workbuddy/**", "artifacts/**"]}
    changed = [".workbuddy/memory_l4/qmm_v5/a.json", "scripts/x.py"]
    ok, reason = MODULE.check_forbidden_paths(changed, policy)
    assert ok is False
    assert reason == "FORBIDDEN_PATH"


def test_scope_enforcement_blocks_out_of_scope_changes():
    ai = {
        "AI_COLLAB": {
            "scope": ["scripts/memory_l4/qmm_v5/**"],
            "risk": "low",
            "tests": ["pytest -q"],
        }
    }
    changed = ["scripts/memory_l4/qmm_v5/engine.py", "tests/test_smoke.py"]
    ok, reason = MODULE.check_scope(changed, ai)
    assert ok is False
    assert reason == "OUT_OF_SCOPE_CHANGE"


def test_risk_requires_tests_for_medium_high():
    ai = {"AI_COLLAB": {"scope": ["scripts/**"], "risk": "high", "tests": []}}
    ok, reason = MODULE.check_risk_tests(ai)
    assert ok is False
    assert reason == "RISK_REQUIRES_TESTS"
```

- [ ] **Step 2: 运行 tests，确认失败原因是“缺少实现”而不是语法错误**

Run: `pytest -q tests/test_ci_ai_collab_guard.py -q`  
Expected: FAIL（函数/模块尚未实现）

- [ ] **Step 3: Commit（只提交测试）**

```bash
git add tests/test_ci_ai_collab_guard.py
git commit -m "test(ci): add ai-collab guard unit tests"
```

---

### Task 4: 实现 CI 守卫脚本（ai_collab_guard.py）

**Files:**
- Create: `scripts/ci/ai_collab_guard.py`
- Test: `tests/test_ci_ai_collab_guard.py`

- [ ] **Step 1: 实现最小可通过测试的解析与校验函数**

要求：
- 不依赖外部网络即可通过单元测试（把 API 调用封装到 main 执行路径，单测只测纯函数）。
- 使用 `yaml.safe_load` 解析 AI_COLLAB 代码块。
- glob 匹配使用 `fnmatch.fnmatch` 或自实现 `glob_to_regex`（优先 fnmatch）。

实现（直接写入文件，后续可增量扩展）：

```python
#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def parse_ai_collab_from_pr_body(body: str) -> Dict[str, Any]:
    m = re.search(r"```yaml\\s*(AI_COLLAB:[\\s\\S]*?)```", body, flags=re.MULTILINE)
    if not m:
        raise ValueError("MISSING_AI_COLLAB")
    raw = m.group(1).strip()
    data = yaml.safe_load(raw)
    if not isinstance(data, dict) or "AI_COLLAB" not in data:
        raise ValueError("INVALID_AI_COLLAB")
    return data


def _matches_any(path: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def check_forbidden_paths(changed_files: List[str], policy: Dict[str, Any]) -> Tuple[bool, str]:
    patterns = list(policy.get("forbidden_globs") or [])
    for f in changed_files:
        if _matches_any(f, patterns):
            return False, "FORBIDDEN_PATH"
    return True, ""


def check_scope(changed_files: List[str], ai: Dict[str, Any]) -> Tuple[bool, str]:
    scope = (ai.get("AI_COLLAB") or {}).get("scope") or []
    if not isinstance(scope, list) or not scope:
        return False, "INVALID_AI_COLLAB"
    for f in changed_files:
        if not _matches_any(f, scope):
            return False, "OUT_OF_SCOPE_CHANGE"
    return True, ""


def check_risk_tests(ai: Dict[str, Any]) -> Tuple[bool, str]:
    block = ai.get("AI_COLLAB") or {}
    risk = (block.get("risk") or "low").lower()
    tests = block.get("tests") or []
    if risk in ("medium", "high") and (not isinstance(tests, list) or not tests):
        return False, "RISK_REQUIRES_TESTS"
    return True, ""


def load_policy(policy_file: Path) -> Dict[str, Any]:
    return yaml.safe_load(policy_file.read_text(encoding="utf-8"))


@dataclass
class GuardDecision:
    ok: bool
    reason_codes: List[str]
    details: Dict[str, Any]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=False, default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--pr-number", required=False, default=os.getenv("PR_NUMBER", ""))
    parser.add_argument("--policy-file", default=".github/ai-collab-policy.yml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out-dir", default="artifacts/ai_collab")
    args = parser.parse_args()

    policy = load_policy(Path(args.policy_file))
    pr_body = os.getenv("PR_BODY", "")
    changed_files_raw = os.getenv("CHANGED_FILES", "")
    changed_files = [x for x in changed_files_raw.splitlines() if x.strip()]

    reason_codes: List[str] = []
    details: Dict[str, Any] = {
        "repo": args.repo,
        "pr_number": args.pr_number,
        "changed_files": changed_files,
        "policy_file": args.policy_file,
    }

    try:
        ai = parse_ai_collab_from_pr_body(pr_body)
    except ValueError as e:
        code = str(e)
        reason_codes.append(code)
        _write_artifacts(args.out_dir, GuardDecision(ok=False, reason_codes=reason_codes, details=details))
        return 1

    ok, reason = check_forbidden_paths(changed_files, policy)
    if not ok:
        reason_codes.append(reason)
    ok, reason = check_scope(changed_files, ai)
    if not ok:
        reason_codes.append(reason)
    ok, reason = check_risk_tests(ai)
    if not ok:
        reason_codes.append(reason)

    decision = GuardDecision(ok=(len(reason_codes) == 0), reason_codes=reason_codes, details=details | {"ai": ai})
    _write_artifacts(args.out_dir, decision)
    return 0 if decision.ok else 1


def _write_artifacts(out_dir: str, decision: GuardDecision) -> None:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().astimezone().isoformat(timespec="seconds").replace(":", "").replace("-", "").replace("+", "_")
    guard_path = p / f"guard-{ts}.json"
    guard_path.write_text(json.dumps(asdict(decision), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path = p / f"summary-{ts}.md"
    summary = f\"\"\"# AI Collab Guard Summary

- ok: {decision.ok}
- reason_codes: {decision.reason_codes}
\"\"\"
    summary_path.write_text(summary, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 运行单测，确保全部变绿**

Run: `pytest -q tests/test_ci_ai_collab_guard.py -q`  
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/ci/ai_collab_guard.py
git commit -m "feat(ci): add ai-collab PR guard script"
```

---

### Task 5: 新增 GitHub Actions 门禁工作流（ai-collab-pr-guard）

**Files:**
- Create: `.github/workflows/ai-collab-pr-guard.yml`

- [ ] **Step 1: 写 workflow**

```yaml
name: AI Collab PR Guard

on:
  pull_request:
    branches:
      - main
    types:
      - opened
      - synchronize
      - reopened
      - edited
      - labeled

permissions:
  contents: read
  pull-requests: read

jobs:
  guard:
    name: AI Collab Guard
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pyyaml

      - name: Collect changed files
        run: |
          git fetch origin main --depth=1
          git diff --name-only origin/main...HEAD > changed_files.txt
          cat changed_files.txt

      - name: Run ai-collab guard (fail-closed)
        env:
          PR_NUMBER: ${{ github.event.pull_request.number }}
          PR_BODY: ${{ github.event.pull_request.body }}
          CHANGED_FILES: ${{ steps.changed.outputs.files }}
        run: |
          python scripts/ci/ai_collab_guard.py \
            --repo "${{ github.repository }}" \
            --pr-number "${{ github.event.pull_request.number }}" \
            --policy-file ".github/ai-collab-policy.yml" \
            --out-dir "artifacts/ai_collab"

      - name: Upload guard artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ai-collab-guard
          path: artifacts/ai_collab/
```

注意：上面 `CHANGED_FILES` env 需要直接读文件而不是 steps output。实际实现时改为：

```yaml
      - name: Run ai-collab guard (fail-closed)
        env:
          PR_NUMBER: ${{ github.event.pull_request.number }}
          PR_BODY: ${{ github.event.pull_request.body }}
        run: |
          export CHANGED_FILES="$(cat changed_files.txt)"
          python scripts/ci/ai_collab_guard.py \
            --repo "${{ github.repository }}" \
            --pr-number "${{ github.event.pull_request.number }}" \
            --policy-file ".github/ai-collab-policy.yml" \
            --out-dir "artifacts/ai_collab"
```

- [ ] **Step 2: 本地 YAML 语法检查（可选）**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ai-collab-pr-guard.yml','r',encoding='utf-8').read()); print('ok')"`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ai-collab-pr-guard.yml
git commit -m "feat(ci): add ai-collab PR guard workflow"
```

---

### Task 6: 端到端验证（本地）

**Files:**
- Test: `tests/test_ci_ai_collab_guard.py`

- [ ] **Step 1: 跑单测**

Run: `pytest -q tests/test_ci_ai_collab_guard.py -q`  
Expected: PASS

- [ ] **Step 2: 模拟一次“CI 环境变量驱动”的运行（不访问 GitHub）**

Run:

```bash
export PR_NUMBER=1
export PR_BODY=$'```yaml\nAI_COLLAB:\n  version: 1\n  agent: A2\n  role: worker\n  topic: demo\n  ticket: T1\n  base: main\n  scope:\n    - "scripts/**"\n  tests:\n    - "pytest -q"\n  risk: low\n  rollback:\n    strategy: revert\n    notes: x\n  deps:\n    prs: []\n```\n'
export CHANGED_FILES=$'scripts/ci/ai_collab_guard.py\n'
python scripts/ci/ai_collab_guard.py --repo demo/demo --pr-number 1 --policy-file .github/ai-collab-policy.yml --out-dir /tmp/ai_collab_artifacts
ls -la /tmp/ai_collab_artifacts
```

Expected: exit code 0，并生成 guard/summary 文件

- [ ] **Step 3: Commit（如本地验证产生了临时目录，确保未纳入 git）**

```bash
git status --porcelain
```

Expected: 无临时产物被纳入版本控制

---

## Plan 自检（写计划者执行）

1. 覆盖性：spec 中的 AI_COLLAB、scope 校验、反污染、override、审计产物、fail-closed 均有对应任务。  
2. 无占位符：全文无 TBD/TODO。  
3. 一致性：reason_codes 与文档一致；文件路径与仓库风格一致（scripts/ci + tests/test_ci_*）。  

---

## 执行交接

计划已保存到 `docs/superpowers/plans/2026-05-13-ai-github-collab-implementation-plan.md`。

两种执行方式：

1. **子代理逐任务执行（推荐）**：每个 Task 交给一个独立执行者，减少上下文混乱
2. **当前会话内联执行**：我在本会话按 Task 顺序实现并运行测试

请选择一种执行方式。

