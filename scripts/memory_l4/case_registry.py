import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.memory_l4.paths import memory_l4_cases_dir, workspace_root


def _require_nonempty(value: str, field: str) -> str:
    if not value:
        raise ValueError(f"missing required field: {field}")
    return value


def create_case_from_episode_data(episode: Dict[str, Any], case_id: str) -> Dict[str, Any]:
    ts = _require_nonempty(str(episode.get("ts") or ""), "ts")
    inst_id = _require_nonempty(str(episode.get("inst_id") or ""), "inst_id")
    trace_id = _require_nonempty(str(episode.get("trace_id") or ""), "trace_id")

    return {
        "case_id": case_id,
        "version": "v0.1",
        "ts_start": ts,
        "ts_end": None,
        "inst_id": inst_id,
        "tags": ["auto_case", "episode_ref"],
        "intent": {"question": "", "goal": "", "constraints": []},
        "investigation": {"summary": "", "sources": []},
        "theory_refs": [],
        "environment_snapshot": {"regime": ""},
        "plan": {
            "minimal_change": "",
            "max_future_space": "",
            "steps": ["补全意图/调查/复盘/象限坐标"]
        },
        "execution": {
            "episode_refs": [{"trace_id": trace_id, "path": ""}],
            "result": str(episode.get("status") or episode.get("decision") or "")
        },
        "online_pressure_test": None,
        "rollout_monitoring": None,
        "backtest": None,
        "review": {
            "summary": "",
            "theory_practice_consistency": "partially_consistent",
            "lessons": []
        },
        "dream_reflection": None,
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
        }
    }


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def derive_case_id_from_episode_path(episode_path: Path) -> str:
    return f"TC_{episode_path.stem}"


def _to_repo_relative_path(path: Path) -> str:
    root = workspace_root()
    try:
        return str(path.resolve().relative_to(root.resolve()).as_posix())
    except Exception:
        return str(path.as_posix())


def create_case_from_episode_file(episode_path: Path, out_path: Optional[Path] = None) -> Path:
    episode = load_json(episode_path)
    case_id = derive_case_id_from_episode_path(episode_path)
    if out_path is None:
        out_path = memory_l4_cases_dir() / f"{case_id}.json"

    data = create_case_from_episode_data(episode, case_id=case_id)
    data["execution"]["episode_refs"][0]["path"] = _to_repo_relative_path(episode_path)

    save_json(out_path, data)
    return out_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    episode_path = Path(args.episode)
    out_path = Path(args.out) if args.out else None

    created = create_case_from_episode_file(episode_path, out_path=out_path)
    print(str(created))


if __name__ == "__main__":
    main()
