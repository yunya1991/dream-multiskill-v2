from __future__ import annotations

from typing import Any, Callable, Dict


ERROR_CODES = {
    "CONSTRAINT_VALIDATION_FAILED",
    "MEMORY_REFERENCE_MISSING",
    "EVIDENCE_INCOMPLETE",
    "SANDBOX_REGRESSION",
}


class TradingStateMachine:
    VALID = {
        "IDLE": {"SIGNAL"},
        "SIGNAL": {"RESEARCH"},
        "RESEARCH": {"SIMULATION"},
        "SIMULATION": {"VALIDATION"},
        "VALIDATION": {"EXECUTION"},
        "EXECUTION": {"GOVERNANCE", "IDLE"},
        "GOVERNANCE": {"RESEARCH", "SIMULATION", "IDLE"},
    }

    def __init__(self) -> None:
        self.current = "IDLE"

    def transition(self, new_state: str) -> str:
        allowed = self.VALID.get(self.current, set())
        if new_state not in allowed:
            raise ValueError(f"invalid transition: {self.current} -> {new_state}")
        self.current = new_state
        return self.current


class ReputationLedger:
    def __init__(self) -> None:
        self._scores: Dict[str, int] = {}

    def penalize(self, module_name: str, delta: int = 5) -> int:
        self._scores[module_name] = max(0, self.score(module_name) - delta)
        return self._scores[module_name]

    def recover(self, module_name: str, delta: int = 1) -> int:
        self._scores[module_name] = min(100, self.score(module_name) + delta)
        return self._scores[module_name]

    def score(self, module_name: str) -> int:
        return self._scores.get(module_name, 100)


def execute_with_retry(
    fn: Callable[[], Any],
    *,
    max_retries: int,
    ledger: ReputationLedger,
    module_name: str,
) -> Dict[str, Any]:
    attempts = 0
    while True:
        attempts += 1
        try:
            result = fn()
            ledger.recover(module_name)
            return {"status": "OK", "attempts": attempts, "result": result}
        except Exception as exc:  # noqa: BLE001
            code = str(exc) if str(exc) in ERROR_CODES else "SANDBOX_REGRESSION"
            ledger.penalize(module_name)
            if attempts > max_retries:
                return {
                    "status": "DEGRADED",
                    "attempts": attempts,
                    "error_code": code,
                }
