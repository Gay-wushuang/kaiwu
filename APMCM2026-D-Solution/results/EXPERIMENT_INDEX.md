# 真机实验索引

本文件只做**记录归档**，不重算、不推断、不补造任何实验数据。
所有任务名称、任务 ID、设备型号、时间与硬件时长均取自 `results/vendor_reports/*.pdf` 原文。
缺失文件一律标记 `MISSING`；正式实验的数据解码与科学分析由参赛队员独立完成。

- 索引建立时间：2026-11-27
- 对应代码版本：`db624f1`（工程分支基于此提交）
- 原始报告目录：`results/vendor_reports/`

---

## 1. 任务总表

| # | 任务名称 | 任务 ID | 设备型号 | 提交时间 | 结束时间 | 硬件时长 | 模式 | 返回样本 | 合法样本 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `apmcm_q2_no2_k13` | `4cc56fdeb17d4fdc95cbdd1d436ffeef` | SPQC-550 | 2026-11-26 14:11:16 | 2026-11-26 14:11:28 | 0.6673 ms | 优化 | 7 | 2 |
| 2 | `apmcm_q2_k13_m3x` | `fa769c1bf4974f5594c357ada1bf4d5a` | SPQC-550 | 2026-11-26 14:40:12 | 2026-11-26 14:40:16 | 0.9798 ms | 优化 | 10 | 1 |
| 3 | `apmcm_q2_k8_m1x` | `3d77a22670424dc7be3ff1872e2db416` | SPQC-1000 | 2026-11-26 14:47:39 | 2026-11-26 14:47:43 | 0.8221 ms | 优化 | 10 | 1 |

三个任务各消耗 1 次优化配额。设备型号由平台调度，SDK 不支持指定机型。

---

## 2. 文件关联

### 任务 1：apmcm_q2_no2_k13

| 类别 | 路径 | 状态 |
|---|---|---|
| 原始 PDF 报告 | `results/vendor_reports/apmcm_q2_no2_k13.pdf` | 存在 |
| 统计文件 | `results/cim_stats/apmcm_q2_no2_k13_stats.json` | **MISSING** |
| 逐样本记录 | `results/cim_samples/apmcm_q2_no2_k13_samples.csv` | **MISSING** |
| 结果 CSV | `results/apmcm_q2_no2_k13_result.csv` | **MISSING** |
| 运行日志 | `results/logs/cim_run_k13.log` | 存在（含 7 个解与 V̂） |
| 人工整理表 | `results/official_task_report.csv` | 存在（转录，非原始导出；已与 PDF 核对） |
| H 分布图 | `figures/apmcm_q2_no2_k13_H_hist.png` | **MISSING** |

### 任务 2：apmcm_q2_k13_m3x

| 类别 | 路径 | 状态 |
|---|---|---|
| 原始 PDF 报告 | `results/vendor_reports/apmcm_q2_k13_m3x.pdf` | 存在 |
| 统计文件 | `results/cim_stats/apmcm_q2_k13_m3x_stats.json` | 存在 |
| 逐样本记录 | `results/cim_samples/apmcm_q2_k13_m3x_samples.csv` | 存在 |
| 结果 CSV | `results/apmcm_q2_k13_m3x_result.csv` | **MISSING**（该脚本路径未落盘 result.csv） |
| 运行日志 | `results/logs/run_m3x.log` | 存在（结果下载 SSL 中断） |
| 重试日志 | `results/logs/run_m3x_retry.log` | 存在（复用同名同矩阵任务，未新建任务） |
| H 分布图 | `figures/apmcm_q2_k13_m3x_H_hist.png` | 存在 |

### 任务 3：apmcm_q2_k8_m1x

| 类别 | 路径 | 状态 |
|---|---|---|
| 原始 PDF 报告 | `results/vendor_reports/apmcm_q2_k8_m1x.pdf` | 存在 |
| 统计文件 | `results/cim_stats/apmcm_q2_k8_m1x_stats.json` | 存在 |
| 逐样本记录 | `results/cim_samples/apmcm_q2_k8_m1x_samples.csv` | 存在 |
| 结果 CSV | `results/apmcm_q2_k8_m1x_result.csv` | **MISSING**（该脚本路径未落盘 result.csv） |
| 运行日志 | `results/logs/run_k8.log` | 存在 |
| H 分布图 | `figures/apmcm_q2_k8_m1x_H_hist.png` | 存在 |

---

## 3. 未成功的提交

| 任务名称 | 结果 | 证据 |
|---|---|---|
| `apmcm_q2_k13_samp200` | 任务创建失败：采样模式配额不足，未生成任务、未消耗配额 | `results/logs/run_samp200.log` |

---

## 4. 缺失项汇总

1. `apmcm_q2_no2_k13`：统计 JSON、逐样本 CSV、结果 CSV、H 分布图均 MISSING。
2. `apmcm_q2_k13_m3x`、`apmcm_q2_k8_m1x`：`*_result.csv` MISSING（逐样本 CSV 已存在，可作为替代记录）。
3. 平台导出的 `.pkl` 结果文件（PDF 中引用的文件名）未入库。
4. 所有缺失项均不补造；如需补齐，应由参赛队员依据原始 PDF 与平台记录独立完成。

---

## 5. 与论文表 15 的差异（仅报告，不改结论）

| 项目 | 论文表 15 | PDF 原文 |
|---|---|---|
| 硬件时长 | 三行均为 0.6673 ms | 0.6673 / 0.9798 / 0.8221 ms |
| 设备型号 | 正文称三组均在 SPQC-550 | 任务 3 为 SPQC-1000 |

差异已记录在 `docs/ENGINEERING_ACCEPTANCE.md` 第 7 节，等待参赛队员确认。
