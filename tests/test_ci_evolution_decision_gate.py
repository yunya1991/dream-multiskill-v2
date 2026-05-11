import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(rel_path: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_decision_gate_approve_writes_decision_promotion_and_pointer(tmp_path):
    mod = _load_module("scripts/ci/evolution_decision_gate.py")
    candidate = {
        "candidate_id": "cand-001",
        "trace_id": "trace-001",
        "constraint_version_base": "v0.1",
        "evidence_refs": ["artifacts/evolution/audit/audit_001.json"],
        "schema_version": "evolution-p0-candidate-v0.1",
    }
    audit = {"candidate_id": "cand-001", "stage": "audit", "pass": True, "violations": []}
    sandbox = {"candidate_id": "cand-001", "stage": "sandbox", "pass": True, "violations": []}

    candidate_path = tmp_path / "candidate.json"
    audit_path = tmp_path / "audit.json"
    sandbox_path = tmp_path / "sandbox.json"
    _write_json(candidate_path, candidate)
    _write_json(audit_path, audit)
    _write_json(sandbox_path, sandbox)

    decision_dir = tmp_path / "decision"
    rollback_dir = tmp_path / "rollback"
    rc = mod.main(
        [
            "--candidate",
            str(candidate_path),
            "--reports",
            f"{audit_path},{sandbox_path}",
            "--to-version",
            "v0.1.1",
            "--artifacts-dir",
            str(decision_dir),
            "--rollback-dir",
            str(rollback_dir),
            "--timestamp",
            "2026-05-12T08:00:00Z",
        ]
    )
    assert rc == 0

    decision_file = decision_dir / "decision-20260512T080000Z.json"
    promotion_file = decision_dir / "promotion-20260512T080000Z.json"
    pointer_file = rollback_dir / "rollback-pointer-20260512T080000Z.json"
    assert decision_file.exists()
    assert promotion_file.exists()
    assert pointer_file.exists()

    decision_payload = json.loads(decision_file.read_text(encoding="utf-8"))
    assert decision_payload["decision"] == "approve"
    assert decision_payload["rollback_pointer_id"].startswith("rp-cand-001-")


def test_decision_gate_rejects_when_required_stage_missing(tmp_path):
    mod = _load_module("scripts/ci/evolution_decision_gate.py")
    candidate = {
        "candidate_id": "cand-002",
        "trace_id": "trace-002",
        "constraint_version_base": "v0.1",
        "evidence_refs": ["artifacts/evolution/audit/audit_002.json"],
        "schema_version": "evolution-p0-candidate-v0.1",
    }
    audit = {"candidate_id": "cand-002", "stage": "audit", "pass": True, "violations": []}

    candidate_path = tmp_path / "candidate.json"
    audit_path = tmp_path / "audit.json"
    _write_json(candidate_path, candidate)
    _write_json(audit_path, audit)

    decision_dir = tmp_path / "decision"
    rc = mod.main(
        [
            "--candidate",
            str(candidate_path),
            "--reports",
            str(audit_path),
            "--to-version",
            "v0.1.1",
            "--artifacts-dir",
            str(decision_dir),
            "--rollback-dir",
            str(tmp_path / "rollback"),
            "--timestamp",
            "2026-05-12T08:01:00Z",
        ]
    )
    assert rc == 1

    decision_file = decision_dir / "decision-20260512T080100Z.json"
    assert decision_file.exists()
    payload = json.loads(decision_file.read_text(encoding="utf-8"))
    assert payload["decision"] == "reject"
    assert "REPORT_STAGE_MISSING" in payload["reason_codes"]
    assert not (decision_dir / "promotion-20260512T080100Z.json").exists()


def test_decision_gate_rejects_when_report_has_violation(tmp_path):
    mod = _load_module("scripts/ci/evolution_decision_gate.py")
    candidate = {
        "candidate_id": "cand-003",
        "trace_id": "trace-003",
        "constraint_version_base": "v0.1",
        "evidence_refs": ["artifacts/evolution/audit/audit_003.json"],
        "schema_version": "evolution-p0-candidate-v0.1",
    }
    audit = {"candidate_id": "cand-003", "stage": "audit", "pass": True, "violations": []}
    sandbox = {
        "candidate_id": "cand-003",
        "stage": "sandbox",
        "pass": True,
        "violations": ["regression-detected"],
    }

    candidate_path = tmp_path / "candidate.json"
    audit_path = tmp_path / "audit.json"
    sandbox_path = tmp_path / "sandbox.json"
    _write_json(candidate_path, candidate)
    _write_json(audit_path, audit)
    _write_json(sandbox_path, sandbox)

    rc = mod.main(
        [
            "--candidate",
            str(candidate_path),
            "--reports",
            f"{audit_path},{sandbox_path}",
            "--to-version",
            "v0.1.1",
            "--artifacts-dir",
            str(tmp_path / "decision"),
            "--rollback-dir",
            str(tmp_path / "rollback"),
            "--timestamp",
            "2026-05-12T08:02:00Z",
        ]
    )
    assert rc == 1
