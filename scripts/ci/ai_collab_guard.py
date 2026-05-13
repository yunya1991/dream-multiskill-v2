#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def parse_ai_collab_from_pr_body(body: str) -> Dict[str, Any]:
    m = re.search(r"```yaml\s*(AI_COLLAB:[\s\S]*?)```", body, flags=re.MULTILINE)
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
    data = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def evaluate_guard(
    *,
    pr_body: str,
    changed_files: List[str],
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    reason_codes: List[str] = []
    details: Dict[str, Any] = {"changed_files": changed_files}

    try:
        ai = parse_ai_collab_from_pr_body(pr_body)
    except ValueError as e:
        reason_codes.append(str(e))
        return {"ok": False, "reason_codes": reason_codes, "details": details}

    ok, reason = check_forbidden_paths(changed_files, policy)
    if not ok:
        reason_codes.append(reason)
    ok, reason = check_scope(changed_files, ai)
    if not ok:
        reason_codes.append(reason)
    ok, reason = check_risk_tests(ai)
    if not ok:
        reason_codes.append(reason)

    details["ai"] = ai
    return {"ok": (len(reason_codes) == 0), "reason_codes": reason_codes, "details": details}


def write_artifacts(out_dir: Path, decision: Dict[str, Any]) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().astimezone().isoformat(timespec="seconds").replace(":", "").replace("-", "").replace("+", "_")

    guard_path = out_dir / f"guard-{ts}.json"
    guard_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_path = out_dir / f"summary-{ts}.md"
    summary_path.write_text(
        "\n".join(
            [
                "# AI Collab Guard Summary",
                "",
                f"- ok: {bool(decision.get('ok'))}",
                f"- reason_codes: {decision.get('reason_codes')}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"guard": str(guard_path), "summary": str(summary_path)}


def _split_lines(value: str) -> List[str]:
    return [x.strip() for x in value.splitlines() if x.strip()]


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--pr-number", default=os.getenv("PR_NUMBER", ""))
    parser.add_argument("--policy-file", default=".github/ai-collab-policy.yml")
    parser.add_argument("--out-dir", default="artifacts/ai_collab")
    args = parser.parse_args(argv)

    policy_path = Path(args.policy_file)
    policy = load_policy(policy_path) if policy_path.exists() else {}

    pr_body = os.getenv("PR_BODY", "")
    changed_files = _split_lines(os.getenv("CHANGED_FILES", ""))

    decision = evaluate_guard(pr_body=pr_body, changed_files=changed_files, policy=policy)
    details = decision.get("details") if isinstance(decision.get("details"), dict) else {}
    details["repo"] = args.repo
    details["pr_number"] = args.pr_number
    details["policy_file"] = args.policy_file
    decision["details"] = details

    write_artifacts(Path(args.out_dir), decision)
    return 0 if bool(decision.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
