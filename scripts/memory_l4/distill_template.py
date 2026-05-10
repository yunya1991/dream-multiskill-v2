import json
from pathlib import Path
import sys
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.memory_l4.paths import memory_l4_distills_dir


def create_distill_template(distill_id: str, supporting_case_ids: List[str], kind: str) -> Dict[str, Any]:
    return {
        "distill_id": distill_id,
        "version": "v0.1",
        "kind": kind,
        "claim": "",
        "supporting_case_ids": supporting_case_ids,
        "actionable_rules": [],
        "quadrant": {
            "x": 0.0,
            "y": 0.0,
            "evidence": {
                "weights": {"perf": 0.4, "consistency": 0.4, "human": 0.2},
                "y_perf": 0.0,
                "y_consistency": 0.0,
                "y_human": 0.0,
                "notes": ""
            }
        },
        "migration_history": []
    }


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--kind", required=True)
    parser.add_argument("--cases", required=True)
    args = parser.parse_args()

    case_ids = [s.strip() for s in args.cases.split(",") if s.strip()]
    data = create_distill_template(args.id, case_ids, kind=args.kind)
    out_path = memory_l4_distills_dir() / f"{args.id}.json"
    save_json(out_path, data)
    print(str(out_path))


if __name__ == "__main__":
    main()

