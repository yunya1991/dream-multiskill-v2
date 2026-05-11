#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REQUIRED_CANDIDATE_FIELDS = [
    "candidate_id",
    "trace_id",
    "constraint_version_base",
    "evidence_refs",
    "schema_version",
]

DEFAULT_REQUIRED_STAGES = ["audit", "sandbox", "stress", "scenario", "backtest"]
DEFAULT_STAGE_POLICY = {
    "require_pass": True,
    "allow_warnings": False,
    "max_violation_count": 0,
    "severity_blocklist": ["high", "critical"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_stage_policy(path: str) -> Dict[str, Dict[str, Any]]:
    if not path:
        return {}
    payload = _load_json(Path(path))
    if not isinstance(payload, dict):
        raise ValueError("stage_policy_json must be a JSON object")
    out: Dict[str, Dict[str, Any]] = {}
    for stage, policy in payload.items():
        if not isinstance(stage, str):
            continue
        if isinstance(policy, dict):
            out[stage] = policy
    return out


def _merged_stage_policy(required_stages: List[str], policy_by_stage: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for stage in required_stages:
        stage_policy = dict(DEFAULT_STAGE_POLICY)
        stage_policy.update(policy_by_stage.get(stage, {}))
        blocklist = stage_policy.get("severity_blocklist", [])
        if not isinstance(blocklist, list):
            blocklist = list(DEFAULT_STAGE_POLICY["severity_blocklist"])
        stage_policy["severity_blocklist"] = [str(item).lower() for item in blocklist if str(item).strip()]
        stage_policy["require_pass"] = bool(stage_policy.get("require_pass", True))
        stage_policy["allow_warnings"] = bool(stage_policy.get("allow_warnings", False))
        stage_policy["max_violation_count"] = int(stage_policy.get("max_violation_count", 0))
        merged[stage] = stage_policy
    return merged


def _collect_violation_severities(violations: Any) -> List[str]:
    if not isinstance(violations, list):
        return []
    severities: List[str] = []
    for item in violations:
        if isinstance(item, dict):
            sev = str(item.get("severity") or "").strip().lower()
            if sev:
                severities.append(sev)
    return severities


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evolution P0 decision gate")
    parser.add_argument("--candidate", required=True, help="Path to Candidate JSON")
    parser.add_argument(
        "--reports",
        required=True,
        help="Comma-separated ValidationReport JSON paths",
    )
    parser.add_argument("--to-version", required=True, help="Target constraint version")
    parser.add_argument("--required-stages", default="audit,sandbox,stress,scenario,backtest")
    parser.add_argument("--stage-policy-json", default="", help="Path to stage policy JSON")
    parser.add_argument("--artifacts-dir", default="artifacts/evolution/decision")
    parser.add_argument("--rollback-dir", default="artifacts/evolution/rollback")
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def validate_candidate(candidate: Dict[str, Any]) -> List[str]:
    reason_codes: List[str] = []
    for key in REQUIRED_CANDIDATE_FIELDS:
        if key not in candidate:
            reason_codes.append("CANDIDATE_INVALID")
            break
    evidence_refs = candidate.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or len(evidence_refs) == 0:
        reason_codes.append("EVIDENCE_MISSING")
    return reason_codes


def evaluate_decision(
    *,
    candidate: Dict[str, Any],
    reports: List[Dict[str, Any]],
    required_stages: List[str],
    stage_policy: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    reason_codes = validate_candidate(candidate)
    stage_map: Dict[str, Dict[str, Any]] = {}
    stage_results: Dict[str, bool] = {}

    for report in reports:
        stage = str(report.get("stage") or "").strip()
        if stage:
            stage_map[stage] = report

    for stage in required_stages:
        report = stage_map.get(stage)
        policy = stage_policy.get(stage, dict(DEFAULT_STAGE_POLICY))
        if report is None:
            reason_codes.append("REPORT_STAGE_MISSING")
            stage_results[stage] = False
            continue
        pass_flag = bool(report.get("pass"))
        violations = report.get("violations", [])
        violation_count = len(violations) if isinstance(violations, list) else 0
        has_violations = violation_count > 0
        severities = _collect_violation_severities(violations)

        stage_ok = True
        if policy.get("require_pass", True) and not pass_flag:
            reason_codes.append("REPORT_NOT_PASSED")
            stage_ok = False
        if has_violations and violation_count > int(policy.get("max_violation_count", 0)):
            reason_codes.append("REPORT_VIOLATION_COUNT_EXCEEDED")
            stage_ok = False
        blocklist = {str(item).lower() for item in policy.get("severity_blocklist", [])}
        if any(sev in blocklist for sev in severities):
            reason_codes.append("REPORT_SEVERITY_BLOCKED")
            stage_ok = False
        if has_violations and not policy.get("allow_warnings", False):
            reason_codes.append("REPORT_VIOLATION_FOUND")
            stage_ok = False
        stage_results[stage] = stage_ok

    # Keep order stable and deduplicate for deterministic artifacts.
    dedup_codes = list(dict.fromkeys(reason_codes))
    decision = "approve" if len(dedup_codes) == 0 else "reject"
    return {
        "decision": decision,
        "reason_codes": dedup_codes,
        "stage_results": stage_results,
    }


def build_rollback_pointer(
    *,
    candidate: Dict[str, Any],
    from_version: str,
    to_version: str,
    evidence_refs: List[str],
    timestamp: str,
) -> Dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id"))
    pointer_id = f"rp-{candidate_id}-{from_version}-to-{to_version}"
    restore_ref = f"constraints/releases/{from_version}.json"
    return {
        "pointer_id": pointer_id,
        "candidate_id": candidate_id,
        "trace_id": str(candidate.get("trace_id") or ""),
        "from_version": from_version,
        "to_version": to_version,
        "constraint_snapshot_ref": restore_ref,
        "restore_ref": restore_ref,
        "restore_command": (
            "python scripts/ci/constraint_rollback.py "
            f"--restore-ref {restore_ref}"
        ),
        "evidence_refs": evidence_refs,
        "created_at": timestamp,
        "schema_version": "evolution-p0-rollback-pointer-v0.1",
    }


def _run(args: argparse.Namespace) -> int:
    timestamp = args.timestamp or _now_iso()
    ts_name = timestamp.replace("-", "").replace(":", "").replace("Z", "Z").replace(".", "")

    candidate_path = Path(args.candidate)
    report_paths = [Path(item.strip()) for item in str(args.reports).split(",") if item.strip()]
    required_stages = [item.strip() for item in str(args.required_stages).split(",") if item.strip()]
    if not required_stages:
        required_stages = list(DEFAULT_REQUIRED_STAGES)
    stage_policy = _merged_stage_policy(required_stages, _load_stage_policy(str(args.stage_policy_json)))

    candidate = _load_json(candidate_path)
    reports = [_load_json(path) for path in report_paths]
    gate_result = evaluate_decision(
        candidate=candidate,
        reports=reports,
        required_stages=required_stages,
        stage_policy=stage_policy,
    )

    decision_record: Dict[str, Any] = {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "trace_id": str(candidate.get("trace_id") or ""),
        "decision": gate_result["decision"],
        "reason_codes": gate_result["reason_codes"],
        "required_stages": required_stages,
        "stage_policy_snapshot": stage_policy,
        "stage_results": gate_result["stage_results"],
        "rollback_pointer_id": "",
        "timestamp": timestamp,
        "schema_version": "evolution-p0-decision-record-v0.1",
    }

    promotion_record: Optional[Dict[str, Any]] = None
    rollback_pointer: Optional[Dict[str, Any]] = None

    if gate_result["decision"] == "approve":
        from_version = str(candidate.get("constraint_version_base") or "")
        evidence_refs = [str(item) for item in candidate.get("evidence_refs", []) if str(item).strip()]
        rollback_pointer = build_rollback_pointer(
            candidate=candidate,
            from_version=from_version,
            to_version=str(args.to_version),
            evidence_refs=evidence_refs,
            timestamp=timestamp,
        )
        decision_record["rollback_pointer_id"] = rollback_pointer["pointer_id"]
        promotion_record = {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "from_version": from_version,
            "to_version": str(args.to_version),
            "decision": "approve",
            "rollback_pointer": f"{args.rollback_dir}/rollback-pointer-{ts_name}.json",
            "evidence_refs": evidence_refs,
            "timestamp": timestamp,
        }

    if not args.dry_run:
        decision_out = Path(args.artifacts_dir) / f"decision-{ts_name}.json"
        _write_json(decision_out, decision_record)
        if rollback_pointer is not None:
            rollback_out = Path(args.rollback_dir) / f"rollback-pointer-{ts_name}.json"
            _write_json(rollback_out, rollback_pointer)
        if promotion_record is not None:
            promotion_out = Path(args.artifacts_dir) / f"promotion-{ts_name}.json"
            _write_json(promotion_out, promotion_record)

    print(json.dumps(decision_record, ensure_ascii=False))
    return 0 if gate_result["decision"] == "approve" else 1


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
