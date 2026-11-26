# 独立复现归档（2026-11-27）

本目录保存**独立复现环境**的端到端输出，与仓库根目录下 `results/` 中的**队友原始实验**严格分离，互不覆盖。

## 来源

- 代码版本：`822b7ea`（`engineering/reproducibility`）
- 运行目录：`%TEMP%\apmcm_e2e`（临时副本，避免覆盖仓库产物）
- 命令：`python code/run_all.py`
- 环境：CPython 3.12.6，依赖见仓库根目录 `requirements.lock.txt`
- 数据：仓库 `date/`，8 个 CSV 的 SHA256 均与官方 `sha256_public.json` 一致
- 运行耗时：74.0 s

## 文件

| 文件 | 说明 |
|---|---|
| `final_answers.json` | 本次复现的机器可读汇总 |
| `FINAL_ANSWERS.md` | 本次复现的人类可读汇总 |
| `run_all.log` | 本次复现的运行日志 |
| `submission_q1_holdout.csv` | 问题 1 holdout 预测（3,703 行） |
| `submission_q2_top20.csv` | 问题 2 前 20 候选 |
| `submission_q3_top20.csv` | 问题 3 前 20 候选 |

模型产物在 `models/surrogate_phys.joblib`（已被 `.gitignore` 排除），SHA256 记录在 `results/EXPERIMENT_VERSION.json`。

## 与原始实验的差异

本次复现的指标与原始记录接近但不完全一致，候选排序发生变化。完整差异见 `results/EXPERIMENT_VERSION.json` 的 `differences_vs_original` 与 `docs/ENGINEERING_ACCEPTANCE.md` 第 11 节。

依赖版本差异已如实记录，但**不认定为数值差异的唯一原因**；两者不可相互替代，正式结论仍以参赛队员确认的版本为准。
