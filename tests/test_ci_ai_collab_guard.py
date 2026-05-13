import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(rel_path: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_extract_ai_collab_block_from_fenced_yaml():
    mod = _load_module("scripts/ci/ai_collab_guard.py")
    body = """
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
"""
    data = mod.parse_ai_collab_from_pr_body(body)
    assert data["AI_COLLAB"]["agent"] == "A2"


def test_forbidden_globs_block_paths():
    mod = _load_module("scripts/ci/ai_collab_guard.py")
    policy = {"forbidden_globs": [".workbuddy/**", "artifacts/**"]}
    changed = [".workbuddy/memory_l4/qmm_v5/a.json", "scripts/x.py"]
    ok, reason = mod.check_forbidden_paths(changed, policy)
    assert ok is False
    assert reason == "FORBIDDEN_PATH"


def test_scope_enforcement_blocks_out_of_scope_changes():
    mod = _load_module("scripts/ci/ai_collab_guard.py")
    ai = {
        "AI_COLLAB": {
            "scope": ["scripts/memory_l4/qmm_v5/**"],
            "risk": "low",
            "tests": ["pytest -q"],
        }
    }
    changed = ["scripts/memory_l4/qmm_v5/engine.py", "tests/test_smoke.py"]
    ok, reason = mod.check_scope(changed, ai)
    assert ok is False
    assert reason == "OUT_OF_SCOPE_CHANGE"


def test_risk_requires_tests_for_medium_high():
    mod = _load_module("scripts/ci/ai_collab_guard.py")
    ai = {"AI_COLLAB": {"scope": ["scripts/**"], "risk": "high", "tests": []}}
    ok, reason = mod.check_risk_tests(ai)
    assert ok is False
    assert reason == "RISK_REQUIRES_TESTS"

