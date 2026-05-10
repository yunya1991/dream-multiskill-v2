# Migration Whitelist v1

Source repository: `yunya1991/dream-trading-automation`

## Include

- `workflows/memory/memory_engine/*`
- `scripts/memory_l4/paths.py`
- `scripts/memory_l4/case_registry.py`
- `scripts/memory_l4/distill_template.py`
- `scripts/memory_l4/index_builder.py`
- `scripts/memory_l4/query_similar.py`
- `scripts/memory_l4/stats_builder.py`
- `scripts/memory_l4/dashboard_renderer.py`
- `scripts/memory_l4/migration_mapper.py`
- `scripts/memory_l4/shared_memory_bus.py`
- `scripts/memory_l4/memory_graph.py`
- `scripts/memory_l4/meta_learning_tasks.py`
- `scripts/memory_l4/agent_acl.py`
- `.workbuddy/memory_l4/schemas/*.json`
- `tests/test_memory_l4_*.py`

## Exclude

- Legacy deployment scripts not tied to architecture baseline.
- One-off experimental notebooks or local reports.
- Any module without tests or artifact contract.
