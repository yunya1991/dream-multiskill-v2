# 记忆工作流规范

定义 L1-L4 记忆、复盘、蒸馏、索引与统计的输入输出契约。

## L1~L4 显式入口映射

- `workflows/memory/L1_realtime/entrypoint.py`
  - `run_l1_realtime_retrieval` -> `MemoryEngine.retrieve_for_decision`
  - `run_l1_realtime_relevance` -> `MemoryEngine.build_relevance_matrix`
- `workflows/memory/L2_shortterm/entrypoint.py`
  - `run_l2_shortterm_feedback` -> `MemoryEngine.update_bandit_from_episodes`
  - `run_l2_shortterm_health_check` -> `MemoryEngine.check_consistency + get_health_score`
- `workflows/memory/L3_longterm/entrypoint.py`
  - `run_l3_longterm_maintenance` -> `MemoryEngine.build_vector_artifacts + check_consistency + get_health_score`
- `workflows/memory/L4_archive/entrypoint.py`
  - `run_l4_failure_analysis` -> `MemoryEngine.analyze_failure_memory`
  - `run_l4_cross_market_migration` -> `MemoryEngine.analyze_cross_market_migration`
  - `run_l4_graph_build` -> `MemoryEngine.build_shared_memory_graph`
  - `run_l4_meta_task_enqueue` -> `MemoryEngine.enqueue_meta_learning_tasks`

## 约束

- 入口层只做薄封装，不承载复杂业务逻辑。
- 复杂能力统一下沉至 `workflows/memory/memory_engine/` 与 `scripts/memory_l4/`。
- 所有入口调用应传递 `trace_id`、`evidence_refs` 等主链必需字段（由上游调用方负责组装）。
