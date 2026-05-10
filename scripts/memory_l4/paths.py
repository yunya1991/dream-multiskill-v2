from pathlib import Path


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def workbuddy_dir() -> Path:
    return workspace_root() / ".workbuddy"


def memory_l4_dir() -> Path:
    return workbuddy_dir() / "memory_l4"


def memory_l4_cases_dir() -> Path:
    return memory_l4_dir() / "cases"


def memory_l4_distills_dir() -> Path:
    return memory_l4_dir() / "distills"


def memory_l4_stats_dir() -> Path:
    return memory_l4_dir() / "stats"


def episodes_dir() -> Path:
    return workbuddy_dir() / "episodes"


def artifacts_memory_l4_dir() -> Path:
    return workspace_root() / "artifacts" / "memory_l4"

