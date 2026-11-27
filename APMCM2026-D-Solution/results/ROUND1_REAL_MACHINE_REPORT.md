# 第一轮真机实验报告（基线 B）

**报告生成时间**：2026-11-28（Asia/Shanghai）  
**代码版本**：`main @ 2a56c554f1a62561a883fe83f16d8c8a327b4357`；算法与工程代码未修改  
**模型基线**：B（独立复现模型 + 预测）  
**SDK / Python**：kaiwu `1.4.4` / Python `3.12.5`  
**输入版本**：`B-Q2-NO2`、`B-Q3-O3`、`B-Q3-FO2`（independent_reproduction）  
**设备**：SPQC-550（5/5 由平台报告确认）  
**配额**：优化任务 32，已用 5，剩余 **27**（另有 1 次提交前失败，0 消耗）

## 1. 执行摘要

第一轮共提交 5 次优化任务，全部 `completed`；平台共返回 48 个解向量，其中合法 one-hot 解 11 个、非法解 37 个。五组任务的最低 H 合法解均落在提交前枚举出的 8-bit 适配后并列最优集合内。未提交 Q3 NO2 矩阵；未执行任何重复提交。

| 配置 | 返回 | 合法 | 非法 | 最低 H | 对应合法解 | 硬件耗时 | 端到端耗时 | 状态 |
|---|---:|---:|---:|---:|---|---:|---:|---|
| B_Q2_baseline | 10 | 2 | 8 | -3018 | Ca-Zr | 1.0327 ms | 7.79 s | completed |
| B_Q2_m3x | 10 | 4 | 6 | -3120 | La-B | 13.9135 ms | 7.657 s | completed |
| B_Q2_k8 | 10 | 2 | 8 | -1780 | La-Ti | 10.9816 ms | 7.713 s | completed |
| B_Q3_O3_baseline | 9 | 1 | 8 | -2962 | Ge-Ge | 0.7838 ms | 7.644 s | completed |
| B_Q3_FO2_baseline | 9 | 2 | 7 | -2912 | Sr-Al | 1.2345 ms | 14.016 s | completed |

## 2. 提交配置与矩阵哈希

| 配置 | 输入版本 | topk | mfactor | QUBO/Ising 比特 | 提交矩阵 SHA256 |
|---|---|---:|---:|---|---|
| B_Q2_baseline | B-Q2-NO2 | 13 | 1 | 26 / 27 | `be06017ff8837e0b70886e5bbc049b25c5e61bb17890658da83d58d52d617940` |
| B_Q2_m3x | B-Q2-NO2 | 13 | 3 | 26 / 27 | `e2530a2481d043f7bdcb21b6468a782be4d22f57516b339ae2a9bee80c8d3e73` |
| B_Q2_k8 | B-Q2-NO2 | 8 | 1 | 16 / 17 | `7be3225f2b2473d7c6e16715ffd8277e6ea74accc3637d7fddb37ea984d25d86` |
| B_Q3_O3_baseline | B-Q3-O3 | 13 | 1 | 26 / 27 | `7cd9ce6bef3a22a859a8fc20add93d1520e2d9948fdbdc32bd5f72eab2c903a9` |
| B_Q3_FO2_baseline | B-Q3-FO2 | 13 | 1 | 26 / 27 | `ca295ce6a0b4af05eed472c0f2862e861c055d8214970105ce9b57163dc34b45` |

五组提交矩阵 SHA256 与准备阶段记录逐字一致。Q3 两组的 `topk=13` 由预置哈希反查确认（`topk=12` 无法匹配）。

## 3. 提交前合法指派核验

口径：原始 V 为未量化目标矩阵；8bit 适配后为 SDK `adjust_ising_matrix_precision(I, 8)` 矩阵在全部合法 one-hot 指派上的能量排序，括号内为该指派的原始 V。只枚举合法 one-hot，不是全 Ising 空间基态。

| 配置 | 原始 V=0 最优 | 8bit 适配后并列最优（原始 V） | 交集 | 原始最优名次 |
|---|---|---|---:|---|
| B_Q2_baseline | La-Zr | Sc-Zr（1.105740）、Sc-Hf（2.041916）、Ca-Zr（6.240554）、Ca-Hf（5.880610）、Ca-Nb（5.542586） | 0 | La-Zr #19 |
| B_Q2_m3x | La-Zr | La-In（4.157593）、La-B（9.784210）、Y-In（6.828246）、Y-B（12.621108）、Hf-B（4.635083） | 0 | La-Zr #6 |
| B_Q2_k8 | La-Zr | La-Ti（1.310788）、La-Ta（5.184651）、Ca-Ta（2.884695）、Ba-Ta（3.352174）、Pb-Ta（4.211207） | 0 | La-Zr #6 |
| B_Q3_O3_baseline | Cs-Ta、K-Nb、Pb-Ti | Cs-Ta（0.000000）、Cs-Y（12.090020）、Ge-Ge（2.503005） | 1（Cs-Ta） | Cs-Ta #1，K-Nb #22，Pb-Ti #99 |
| B_Q3_FO2_baseline | Na-Ti、K-Ti | K-Ti（0.000000）、La-Mg（0.081698）、Mg-Al（0.212598）、La-Ca（0.588806）、Ge-Al（1.150540）、La-Al（1.345721）、Sr-Al（1.644446） | 1（K-Ti） | Na-Ti #8，K-Ti #1 |

## 4. 逐任务真机结果

每个任务的原始解向量、能量、平台 PDF、输入矩阵与哈希均在对应归档目录中。样本表按平台返回顺序列出；`置1数` 为 ±1 解向量中 +1 的个数，合法 one-hot 应为 3（1 个 A + 1 个 B + 辅助自旋）。

### 4.1 B_Q2_baseline

- 任务编号：`t20261128-003014-b_q2_baseline-be06017f`
- 平台任务 ID：`44923771c251417d91f15d9841651b4c`
- 设备：SPQC-550；平台创建/结束：2026-11-28 00:30:15 / 2026-11-28 00:30:20
- 硬件运行时长：1.0327 ms；端到端耗时：7.79 s；平台返回：10 个解
- 提交矩阵：`be06017ff8837e0b70886e5bbc049b25c5e61bb17890658da83d58d52d617940`
- 平台报告：`reports/B_Q2_baseline.pdf`（SHA256 `af609f372aee3cc2e674057b1b9ab8d023de9471ae6ccc7f07424f832f665fa2`）
- 归档目录：`e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\experiments\tasks\t20261128-003014-b_q2_baseline-be06017f`

| 样本 | H | 置1数 | aux | A 数 | B 数 | 合法 | 指派 | 原始 V |
|---:|---:|---:|---:|---:|---:|---|---|---:|
| 0 | -3018 | 3 | +1 | 1 | 1 | 是 | Ca-Zr | 6.240554 |
| 1 | -3006 | 3 | +1 | 1 | 1 | 是 | Bi-Sc | 12.497471 |
| 2 | -2938 | 1 | +1 | 0 | 0 | 否 | — | — |
| 3 | -2538 | 7 | +1 | 4 | 2 | 否 | — | — |
| 4 | -2318 | 7 | +1 | 5 | 1 | 否 | — | — |
| 5 | -1858 | 9 | +1 | 6 | 2 | 否 | — | — |
| 6 | -1702 | 10 | +1 | 6 | 3 | 否 | — | — |
| 7 | -1474 | 11 | +1 | 6 | 4 | 否 | — | — |
| 8 | -762 | 13 | +1 | 6 | 6 | 否 | — | — |
| 9 | -270 | 14 | +1 | 7 | 6 | 否 | — | — |

合法解汇总：

| 合法解 | H | 原始 V |
|---|---:|---:|
| Ca-Zr | -3018 | 6.240554 |
| Bi-Sc | -3006 | 12.497471 |

### 4.2 B_Q2_m3x

- 任务编号：`t20261128-003124-b_q2_m3x-e2530a24`
- 平台任务 ID：`a8894d47ec774954ad2c0a3f99634eca`
- 设备：SPQC-550；平台创建/结束：2026-11-28 00:31:25 / 2026-11-28 00:31:29
- 硬件运行时长：13.9135 ms；端到端耗时：7.657 s；平台返回：10 个解
- 提交矩阵：`e2530a2481d043f7bdcb21b6468a782be4d22f57516b339ae2a9bee80c8d3e73`
- 平台报告：`reports/B_Q2_m3x.pdf`（SHA256 `f3173030b0033306bff4d6884fc4037cce656eca6a2b422a343b79277442dab5`）
- 归档目录：`e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\experiments\tasks\t20261128-003124-b_q2_m3x-e2530a24`

| 样本 | H | 置1数 | aux | A 数 | B 数 | 合法 | 指派 | 原始 V |
|---:|---:|---:|---:|---:|---:|---|---|---:|
| 0 | -3120 | 3 | +1 | 1 | 1 | 是 | La-B | 9.784210 |
| 1 | -3116 | 3 | +1 | 1 | 1 | 是 | Hf-Zr | 11.087985 |
| 2 | -3116 | 3 | +1 | 1 | 1 | 是 | La-Nb | 6.607887 |
| 3 | -3112 | 3 | +1 | 1 | 1 | 是 | Li-Zr | 11.000499 |
| 4 | -3084 | 2 | +1 | 1 | 0 | 否 | — | — |
| 5 | -3084 | 2 | +1 | 1 | 0 | 否 | — | — |
| 6 | -3084 | 2 | +1 | 1 | 0 | 否 | — | — |
| 7 | -3084 | 2 | +1 | 0 | 1 | 否 | — | — |
| 8 | -3080 | 2 | +1 | 1 | 0 | 否 | — | — |
| 9 | -3080 | 2 | +1 | 0 | 1 | 否 | — | — |

合法解汇总：

| 合法解 | H | 原始 V |
|---|---:|---:|
| La-B | -3120 | 9.784210 |
| Hf-Zr | -3116 | 11.087985 |
| La-Nb | -3116 | 6.607887 |
| Li-Zr | -3112 | 11.000499 |

### 4.3 B_Q2_k8

- 任务编号：`t20261128-003140-b_q2_k8-7be3225f`
- 平台任务 ID：`6258685cdb1c4541becdb1ae40fac598`
- 设备：SPQC-550；平台创建/结束：2026-11-28 00:31:42 / 2026-11-28 00:31:46
- 硬件运行时长：10.9816 ms；端到端耗时：7.713 s；平台返回：10 个解
- 提交矩阵：`7be3225f2b2473d7c6e16715ffd8277e6ea74accc3637d7fddb37ea984d25d86`
- 平台报告：`reports/B_Q2_k8.pdf`（SHA256 `83ecc1b9d51d2bccf1f0c2da85e211f91c1c5c97020e61b5b140998f6e51c595`）
- 归档目录：`e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\experiments\tasks\t20261128-003140-b_q2_k8-7be3225f`

| 样本 | H | 置1数 | aux | A 数 | B 数 | 合法 | 指派 | 原始 V |
|---:|---:|---:|---:|---:|---:|---|---|---:|
| 0 | -1780 | 3 | +1 | 1 | 1 | 是 | La-Ti | 1.310788 |
| 1 | -1772 | 3 | +1 | 1 | 1 | 是 | La-Al | 3.225792 |
| 2 | -1716 | 4 | +1 | 1 | 2 | 否 | — | — |
| 3 | -1712 | 4 | +1 | 1 | 2 | 否 | — | — |
| 4 | -1692 | 2 | +1 | 1 | 0 | 否 | — | — |
| 5 | -1692 | 2 | +1 | 0 | 1 | 否 | — | — |
| 6 | -1644 | 5 | +1 | 2 | 2 | 否 | — | — |
| 7 | -1624 | 3 | +1 | 2 | 0 | 否 | — | — |
| 8 | -1604 | 1 | +1 | 0 | 0 | 否 | — | — |
| 9 | -1496 | 5 | +1 | 1 | 3 | 否 | — | — |

合法解汇总：

| 合法解 | H | 原始 V |
|---|---:|---:|
| La-Ti | -1780 | 1.310788 |
| La-Al | -1772 | 3.225792 |

### 4.4 B_Q3_O3_baseline

- 任务编号：`t20261128-003159-b_q3_o3_baseline-7cd9ce6b`
- 平台任务 ID：`4a75fbffbe734857b87db54ed346c342`
- 设备：SPQC-550；平台创建/结束：2026-11-28 00:32:01 / 2026-11-28 00:32:05
- 硬件运行时长：0.7838 ms；端到端耗时：7.644 s；平台返回：9 个解
- 提交矩阵：`7cd9ce6bef3a22a859a8fc20add93d1520e2d9948fdbdc32bd5f72eab2c903a9`
- 平台报告：`reports/B_Q3_O3_baseline.pdf`（SHA256 `bd1a7a1094cf72527423c0e69d1f10260cb67c8c2e8872ad4019638e3de7846e`）
- 归档目录：`e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\experiments\tasks\t20261128-003159-b_q3_o3_baseline-7cd9ce6b`

| 样本 | H | 置1数 | aux | A 数 | B 数 | 合法 | 指派 | 原始 V |
|---:|---:|---:|---:|---:|---:|---|---|---:|
| 0 | -2962 | 3 | +1 | 1 | 1 | 是 | Ge-Ge | 2.503005 |
| 1 | -2926 | 4 | +1 | 2 | 1 | 否 | — | — |
| 2 | -2894 | 2 | +1 | 1 | 0 | 否 | — | — |
| 3 | -2870 | 3 | +1 | 2 | 0 | 否 | — | — |
| 4 | -2834 | 1 | +1 | 0 | 0 | 否 | — | — |
| 5 | -2106 | 9 | +1 | 5 | 3 | 否 | — | — |
| 6 | -1026 | 12 | +1 | 4 | 7 | 否 | — | — |
| 7 | 3494 | 17 | +1 | 3 | 13 | 否 | — | — |
| 8 | 5378 | 22 | +1 | 9 | 12 | 否 | — | — |

合法解汇总：

| 合法解 | H | 原始 V |
|---|---:|---:|
| Ge-Ge | -2962 | 2.503005 |

### 4.5 B_Q3_FO2_baseline

- 任务编号：`t20261128-003216-b_q3_fo2_baseline-ca295ce6`
- 平台任务 ID：`87d51d0a3fa14434a80d3bcb63878348`
- 设备：SPQC-550；平台创建/结束：2026-11-28 00:32:17 / 2026-11-28 00:32:27
- 硬件运行时长：1.2345 ms；端到端耗时：14.016 s；平台返回：9 个解
- 提交矩阵：`ca295ce6a0b4af05eed472c0f2862e861c055d8214970105ce9b57163dc34b45`
- 平台报告：`reports/B_Q3_FO2_baseline.pdf`（SHA256 `2a29b0283a927e16da233440a2594a0918f2cfcdec324e53fc090173d2413aa2`）
- 归档目录：`e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\experiments\tasks\t20261128-003216-b_q3_fo2_baseline-ca295ce6`

| 样本 | H | 置1数 | aux | A 数 | B 数 | 合法 | 指派 | 原始 V |
|---:|---:|---:|---:|---:|---:|---|---|---:|
| 0 | -2912 | 3 | +1 | 1 | 1 | 是 | Sr-Al | 1.644446 |
| 1 | -2900 | 3 | +1 | 1 | 1 | 是 | Na-In | 11.218103 |
| 2 | -2868 | 2 | +1 | 1 | 0 | 否 | — | — |
| 3 | -2828 | 1 | +1 | 0 | 0 | 否 | — | — |
| 4 | -2828 | 3 | +1 | 2 | 0 | 否 | — | — |
| 5 | -640 | 13 | +1 | 7 | 5 | 否 | — | — |
| 6 | 8536 | 26 | +1 | 12 | 13 | 否 | — | — |
| 7 | 8540 | 26 | +1 | 12 | 13 | 否 | — | — |
| 8 | 9492 | 27 | +1 | 13 | 13 | 否 | — | — |

合法解汇总：

| 合法解 | H | 原始 V |
|---|---:|---:|
| Sr-Al | -2912 | 1.644446 |
| Na-In | -2900 | 11.218103 |

## 5. 平台报告与归档一致性

| 配置 | 报告解数 | 归档解数 | 向量逐位一致 | H 逐位一致 | PDF SHA256 校验 |
|---|---:|---:|---|---|---|
| B_Q2_baseline | 10 | 10 | 是 | 是 | 是 |
| B_Q2_m3x | 10 | 10 | 是 | 是 | 是 |
| B_Q2_k8 | 10 | 10 | 是 | 是 | 是 |
| B_Q3_O3_baseline | 9 | 9 | 是 | 是 | 是 |
| B_Q3_FO2_baseline | 9 | 9 | 是 | 是 | 是 |

平台 PDF 内含任务 ID、设备、起止时间、硬件运行时长与全部 Hamiltonian/解向量；上述一致性检查在归档时逐任务执行，全部通过。

## 6. 归档清单

归档根目录：`E:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\experiments\tasks\`

| 配置 | 归档目录 | 元数据 | 原始解 | 平台报告 |
|---|---|---|---|---|
| B_Q2_baseline | `t20261128-003014-b_q2_baseline-be06017f` | `task.json` / `config.json` | `raw/solutions.npz`、`raw/solution_energy.csv` | `reports/B_Q2_baseline.pdf` |
| B_Q2_m3x | `t20261128-003124-b_q2_m3x-e2530a24` | `task.json` / `config.json` | `raw/solutions.npz`、`raw/solution_energy.csv` | `reports/B_Q2_m3x.pdf` |
| B_Q2_k8 | `t20261128-003140-b_q2_k8-7be3225f` | `task.json` / `config.json` | `raw/solutions.npz`、`raw/solution_energy.csv` | `reports/B_Q2_k8.pdf` |
| B_Q3_O3_baseline | `t20261128-003159-b_q3_o3_baseline-7cd9ce6b` | `task.json` / `config.json` | `raw/solutions.npz`、`raw/solution_energy.csv` | `reports/B_Q3_O3_baseline.pdf` |
| B_Q3_FO2_baseline | `t20261128-003216-b_q3_fo2_baseline-ca295ce6` | `task.json` / `config.json` | `raw/solutions.npz`、`raw/solution_energy.csv` | `reports/B_Q3_FO2_baseline.pdf` |

每个任务目录统一包含：

```text
task.json, config.json, attempts.jsonl
input/matrix.csv, input/mapping.json, input/manifest.json
input/ising_matrix.csv, input/ising_matrix_raw.csv, input/ising_matrix_raw.npz
input/submitted_mapping.json, input/submitted_target_V.csv, input/hashes.json
raw/solutions.npz, raw/solutions.csv, raw/solution_energy.csv
logs/run.log, reports/<task_name>.pdf, sdk_checkpoints/*.pkl
```

失败尝试归档（保留，未删除）：

- `t20261128-001932-b_q2_baseline-be06017f`：`submit_failed`，`quota_counted=false`，无云端任务、无原始解、无报告。原因：本机缺少 license，SDK 请求 `user_id`/`sdk_code` 时脚本按约定终止。

## 7. 配额

| 项目 | 总额 | 已用 | 剩余 | 依据 |
|---|---:|---:|---:|---|
| 优化任务（OPTIMIZATION） | 32 | 5 | **27** | 本地账本；5 个 `completed` 任务各计 1 |
| 采样任务（SAMPLING） | 0 | 0 | 0 | 本轮未使用 |

提交前用户确认平台优化配额为 32；5 次任务均成功完成，平台侧预计剩余 27，最终以平台控制台余额为准。失败尝试未创建云端任务，不计配额。

## 8. 异常与事实性观察

- 平台返回的非法 one-hot 解共 37/48；各任务非法数：B_Q2_baseline 8、B_Q2_m3x 6、B_Q2_k8 8、B_Q3_O3_baseline 8、B_Q3_FO2_baseline 7。原样归档，未筛选、未重算。
- Q3 两组平台各返回 9 个解（请求 `sample_number=10`），按平台实际返回归档。
- 5 个任务全部调度到 SPQC-550；硬件运行时长 0.78–13.91 ms，端到端耗时 7.64–14.02 s。
- 五组最低 H 合法解均属于第 3 节的 8bit 并列最优集合；Q2 三组的未量化最优 La-Zr 均未以合法 one-hot 解形式返回。
- 未执行 Q3 NO2 矩阵；未修改算法、参数或实验框架；未发生下载失败，未对已创建云端任务重复提交。

## 附录：提交矩阵 SHA256

```text
B_Q2_baseline      be06017ff8837e0b70886e5bbc049b25c5e61bb17890658da83d58d52d617940
B_Q2_m3x           e2530a2481d043f7bdcb21b6468a782be4d22f57516b339ae2a9bee80c8d3e73
B_Q2_k8            7be3225f2b2473d7c6e16715ffd8277e6ea74accc3637d7fddb37ea984d25d86
B_Q3_O3_baseline   7cd9ce6bef3a22a859a8fc20add93d1520e2d9948fdbdc32bd5f72eab2c903a9
B_Q3_FO2_baseline  ca295ce6a0b4af05eed472c0f2862e861c055d8214970105ce9b57163dc34b45
```
