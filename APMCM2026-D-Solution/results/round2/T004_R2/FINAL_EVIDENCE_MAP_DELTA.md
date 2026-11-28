# T004-R2 证据映射增量

本轮无新增平台证据；以下为候选到预检材料的映射。

| 候选 | 配置 | Dry-run | 本地预检 | 预计归档 |
|---|---|---|---|---|
| Q3 O3 lowM direct8 | `REAL_MACHINE_CANDIDATES/CAND_Q3_O3_lowM_direct8.json` | `FINAL_SUBMISSION_PLAN_DRYRUN.txt` | `EXPERIMENTS/R2_CANDIDATE_PRECHECK.json` | `experiments/tasks/<task_id>/` |
| Q3 FO2 lowM direct8 | `.../CAND_Q3_FO2_lowM_direct8.json` | 同上 | 同上 | 同上 |
| G3 Q2 M0 PR tp14 | `.../CAND_G3_Q2_M0_PR_tp14.json` | 同上 | 同上 | 同上 |
| Q3 O3 lowM PR tp14 | `.../CAND_Q3_O3_lowM_PR_tp14.json` | 同上 | 同上 | 同上 |
| Q3 FO2 lowM PR tp14 | `.../CAND_Q3_FO2_lowM_PR_tp14.json` | 同上 | 同上 | 同上 |
| Q2 lowM direct8 repeat | `.../CAND_Q2_lowM_direct8_REPEAT.json` | 同上 | 同上 | 同上 |
| Q2 lowM PR tp14 repeat | `.../CAND_Q2_lowM_PR_tp14_REPEAT.json` | 同上 | 同上 | 同上 |

## 已有证据（不变）

| 内容 | 路径 |
|---|---|
| 7 个正式任务归档 | `experiments/tasks/` |
| 统一指标 | `results/round2/T004_FINAL/FINAL_METRICS.csv` |
| 证据映射 | `results/round2/T004_FINAL/FINAL_EVIDENCE_MAP.md` |
| 数学纠偏 | `results/round2/T004_FINAL/MATH_CORRECTION_REPORT.md` |

## 若执行后的补充位置

每个新任务应新增：

- `experiments/tasks/<task_id>/input/`：输入矩阵、提交矩阵、映射、目标 V。
- `raw/`：原始返回、恢复向量、能量、restore_status。
- `reports/`：平台 PDF。
- `task.json` / `config.json`：设备、硬件时间、平台 ID、配额。
- `FINAL_METRICS_DELTA.csv`：任务级与样本级指标。
- `HARDWARE_RESULTS.md`：新增结果。
