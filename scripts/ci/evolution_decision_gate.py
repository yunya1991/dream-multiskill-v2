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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evolution P0 decision gate")
    parser.add_argument("--candidate", required=True, help="Path to Candidate JSON")
    parser.add_argument(
        "--reports",
        required=True,
        help="Comma-separated ValidationReport JSON paths",
    )
    parser.add_argument("--to-version", required=True, help="Target constraint version")
    parser.add_argument("--required-stages", default="audit,sandbox")
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
        if report is None:
            reason_codes.append("REPORT_STAGE_MISSING")
            stage_results[stage] = False
            continue
        pass_flag = bool(report.get("pass"))
        violations = report.get("violations", [])
        has_violations = isinstance(violations, list) and len(violations) > 0
        if not pass_flag:
            reason_codes.append("REPORT_NOT_PASSED")
        if has_violations:
            reason_codes.append("REPORT_VIOLATION_FOUND")
        stage_results[stage] = pass_flag and not has_violations

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

    candidate = _load_json(candidate_path)
    reports = [_load_json(path) for path in report_paths]
    gate_result = evaluate_decision(candidate=candidate, reports=reports, required_stages=required_stages)

    decision_record: Dict[str, Any] = {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "trace_id": str(candidate.get("trace_id") or ""),
        "decision": gate_result["decision"],
        "reason_codes": gate_result["reason_codes"],
        "required_stages": required_stages,
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
