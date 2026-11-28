# T004-07 主动精度设计核查

- 检查时间：2026-11-28
- 检查范围：工作区 `APMCM2026-D-Solution/` 全部 `.py/.md/.json/.csv`（排除 `.venv`、`site-packages`、
  `experiments/tasks/` 归档内部）
- 关键词：主动精度、整数建模、hardware-aware、integer model、active precision、硬件感知、
  第四路线、第五路线

## 结果

**未发现组员提交的主动整数建模或硬件感知数学建模成果。** 现有精度相关工作只有：

1. 正式 `code/precision_reducer.py` + `code/d_experiment.py` 的 `precision_reducer` 路线（T003 已接入）。
2. PR #5 的 `code/d_precision_reducer.py` 离线验证工具（T003 已核验，明确不进入正式链路）。
3. `results/round2/qubo_refinement/` 的 One-hot/量化误差研究（T002/T003 已完成）。
4. `results/round2/precision_reducer/` 的本地验证与 tp14 真机记录。

没有使用与正式基线 B 不同预测目标、不同候选集或不同数学目标的“主动精度”新路线，因此：

- 不启动第四条/第五条正式技术路线。
- 不把任何离线工具或教学矩阵结果合并进正式实验。
- 若组员后续提交此类成果，应按“独立探索/历史对照”核验，不能直接并入 G1–G4。

## 复核命令

```powershell
Get-ChildItem -Recurse -File -Include *.py,*.md,*.json,*.csv |
  Select-String -Pattern "主动精度|整数建模|hardware-aware|integer model|active precision|硬件感知"
```

当前无命中。
