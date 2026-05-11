# Evolution P0 Acceptance Checklist

## DoD Checklist

- [ ] candidate ingest 可入队并生成 Candidate 契约实例
- [ ] audit gate 可阻断字段/来源/证据链不合格候选
- [ ] sandbox gate 可阻断回归候选
- [ ] decision gate 仅全绿候选可批准
- [ ] promotion 前生成 rollback pointer
- [ ] 每个阶段输出结构化 ValidationReport
- [ ] artifacts 路径可追溯且与候选 ID 对齐

## Acceptance Procedure

1. 使用至少 1 条正样本候选跑通 `C0 -> C7`
2. 使用至少 1 条反样本候选触发 `C_FAIL`
3. 校验两条样本均存在完整 `evidence_refs`
4. 记录验收报告与结论（Go/No-Go）
