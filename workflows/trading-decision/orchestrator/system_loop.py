from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable, Dict, Optional


LoopRunner = Callable[..., Dict[str, Any]]


def _load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _default_runners():
    root = Path(__file__).resolve().parents[1]
    exec_mod = _load_module(root / "orchestrator" / "execution_loop.py", "execution_loop_mod")
    gov_mod = _load_module(root / "orchestrator" / "governance_loop.py", "governance_loop_mod")
    a6_mod = _load_module(root / "A6_intelligence" / "entrypoint.py", "a6_entry_mod")
    return exec_mod.run_execution_loop, a6_mod.run_a6_intelligence, gov_mod.run_governance_loop


def _ship_messages(transport, messages):
    sent = 0
    for message in messages:
        header = message.get("header") or {}
        channel = str(header.get("loop_type") or "execution")
        transport.send(channel, message)
        sent += 1
    return sent


def run_system_loop(
    payload: Dict[str, Any],
    output_dir: Optional[Path] = None,
    *,
    transport: Any,
    execution_runner: Optional[LoopRunner] = None,
    intelligence_runner: Optional[LoopRunner] = None,
    governance_runner: Optional[LoopRunner] = None,
) -> Dict[str, Any]:
    default_execution, default_intelligence, default_governance = _default_runners()
    run_execution = execution_runner or default_execution
    run_intelligence = intelligence_runner or default_intelligence
    run_governance = governance_runner or default_governance

    execution_out = run_execution(payload, output_dir=output_dir)
    intelligence_out = run_intelligence(payload, output_dir=output_dir)
    governance_out = run_governance(payload, output_dir=output_dir)

    message_count = 0
    message_count += _ship_messages(transport, execution_out.get("messages") or [])
    message_count += _ship_messages(transport, intelligence_out.get("messages") or [])
    message_count += _ship_messages(transport, governance_out.get("messages") or [])

    return {
        "trace_id": str(payload.get("trace_id") or "trace-missing"),
        "loops": {
            "execution": execution_out,
            "intelligence": intelligence_out,
            "governance": governance_out,
        },
        "metrics": {
            "loop_count": 3,
            "message_count": message_count,
        },
    }
