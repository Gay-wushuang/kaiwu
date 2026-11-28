# T003-FINAL 集成报告

- 临时集成分支：`integration/t003-final`
- 目标基线：`origin/main` = `b4ed23f`
- 合并内容：
  - `research/precision-reducer` = `c2a1c62`（已包含 `research/qubo-refinement`，未重复合并）
  - PR #5 `ab36818`（离线 PrecisionReducer 验证工具）
  - `origin/main`：已是当前分支祖先，无需额外合并提交
- 真机配额：本轮 0（未新增任务）

## 1. 集成差异

| 来源 | 内容 | 处理 |
|---|---|---|
| `research/precision-reducer` | One-hot V4、PrecisionReducer 工程链路、tp14 真机结果、resume 保护 | 直接保留 |
| PR #5 | `code/d_precision_reducer.py` + `tests/test_precision_reducer.py` | 作为**独立离线验证工具**保留；不替换 `code/precision_reducer.py` 与 `d_experiment.py` 正式路线 |
| `origin/main` | 旧基线 | 已包含，无冲突 |

PR #5 保留的能力：直接 8bit、公开 truncate+split 重放、动态范围压缩
`perform_precision_adaption_mutate`、合法 one-hot 保真指标、恢复契约核对。
其 `CandidateSolver` 仅用于验证矩阵变换与恢复，不是优化器。

PR #5 离线 demo（`PR5_DEMO.json`）：mutate 100 次、DR 11.8767→11.8767
（该教学矩阵无可压缩空间；工具明确注明 mutate 不保证降低动态范围）；
split 41 自旋、恢复 128/128 精确、aux 规范为 +1。该工具仅作离线对照，
不进入 `d_experiment.py` 正式链路，也不用于真机提交。

## 2. 回归结果

| 检查 | 结果 |
|---|---|
| 完整单元测试 | **40/40 OK**（原 34 + PR5 6） |
| direct8 已知哈希（B-Q2-NO2 lowM） | `34f84ed6…` 不变 |
| 旧 JSON 配置（无 precision 字段） | `plan` 通过，行为等同 direct8 |
| 归档完整性 | 7 个任务（6 历史 + 1 PR）矩阵/原始矩阵/解/能量/PDF 哈希全部一致 |
| tp14 PDF 向量 | 10/10 与归档扩展解逐元素一致 |
| 冻结材料 | 未修改 T001/support_materials/预测结果 |

归档核验明细：`results/round2/T003_FINAL/VERIFICATION.json`。

## 3. tp14 严格统计（本轮修正）

| 指标 | 值 |
|---|---:|
| 返回 | 10 |
| 拆分一致 | 2/10 |
| 恢复后 one-hot 合法 | 2/10 |
| 两者同时满足 | 1/10 |
| **严格有效的原始最优命中** | **1/10**（样本 0） |

样本 1 虽恢复为 La-Zr，但扩展态拆分不一致，不计入严格命中。
平台：SPQC-550，硬件 1.5511 ms，平台任务 ID `d833dedb390f4c54ac0c6d7db3bb9b11`，
PDF SHA256 `90365064…`。

## 4. resume 修复

- 问题：对已 `completed` 任务执行 resume，平台查询失败会把状态覆盖为
  `resume_no_result`。
- 修复：`was_completed` 保护；查询失败/空结果/格式异常均保留 `completed`，
  只记录 `last_resume_*` 与 attempts；不覆盖历史解与恢复状态。
- 受影响任务已恢复为 `completed`，历史 `resume_no_result` 尝试仍保留在
  `attempts.jsonl`。
- 新增 `tests/test_resume_guard.py`（2 项）。

## 5. 剩余风险

1. tp14 只有 1 个真机任务，不能估计命中率或跨输入适用性。
2. PrecisionReducer 拆分一致率仍然低；tp12 未提交，G3 未做真机。
3. PR #5 是独立工具，其 `truncated_precision=20` 默认会产生较大扩展矩阵；
   不应直接用于真机提交，正式路线仍以 `d_experiment.py` 为准。
4. 平台账户余额仍以本地账本为准（7/32 已用，剩余 25，`verified=false`）。
5. 集成 PR 尚未由队员确认合并 main。

## 6. 验收结论

- 统一研究基线已形成：One-hot V4 + PrecisionReducer 正式路线 + PR5 离线工具。
- 未修改基线 B、T001 冻结材料和第一轮数据。
- 建议合并 `integration/t003-final` → `main`，由队员最终确认。

## 7. 集成 PR

- PR #7：<https://github.com/Gay-wushuang/kaiwu/pull/7>
- 状态：OPEN、MERGEABLE、CLEAN；**未自动合并**。
- 集成提交：`ebf8a9d`（合并 PR5 提交 `6fd1310`；研究分支 `c2a1c62`）。
- 合并后 `main` 作为 T004 正式对照基线。
