# 最终证据映射（T004-09）

用途：论文负责人从“论文中的数字/表格”追溯到实验 ID、配置、实际提交矩阵、原始返回向量、平台 PDF
和评价结果。所有路径相对 `APMCM2026-D-Solution/`。

## 0. 先确认基线

| 基线 | 路径 | 用途 | 禁止 |
|---|---|---|---|
| **B（正式）** | `results/reproduction_20261127/predictions/` | 正式 Q1/Q2/Q3 结论、真机输入 | 不得与 A 混用 |
| A（历史） | `code/predictions/` | 旧版预测、对照 | 不得用于正式结论 |

- B 的 Q2/Q3 预测 SHA256 见 `results/reproduction_20261127/predictions/SHA256SUMS.txt`。
- B 的 Q1 指标：`results/reproduction_20261127/final_answers.json`（R²=0.824836，MAE=2.571641，
  RMSE=4.597198，Spearman=0.935325，Top-100=40/100）。
- B 的三个交付文件与 A 不同：`results/reproduction_20261127/submission_*.csv` 才是 B 版本。

## 1. Q1

| 论文数字 | 实验/文件 | 实际值 | 证据 |
|---|---|---|---|
| 摘要 R²≈0.825、MAE≈2.58、Spearman≈0.934、Top-100=39 | `results/reproduction_20261127/final_answers.json` | R²=0.8248360139，MAE=2.5716413758，RMSE=4.5971977103，Spearman=0.9353252387，Top-100=**40/100** | `FINAL_METRICS.csv` Q1 行 |
| holdout 3,703 行 | `results/reproduction_20261127/submission_q1_holdout.csv` | 3,703 行；SHA256 `9395cb54…` | `COMPARISON.md` |
| 表 2 四模型对照 | `results/reproduction_20261127/` 与 `reproduction/original_env_20261127/run_20261127/COMPARISON.md` | 论文若给 0.831 等模型对照值，须注明是验证集模型比较，不是基线 B 的最终指标 | — |

## 2. Q2

### 2.1 预测最优

| 论文表述 | 基线 A（旧） | 基线 B（正式） | 来源 |
|---|---|---|---|
| Q2 第一 | LaHfO2N V̂=0.0000 | **LaZrO2N V̂=0.0000** | `results/reproduction_20261127/predictions/pool_q2_phys.csv` |
| Q2 第二 | LaZrO2N V̂=0.0001 | LaHfO2N V̂=0.001396 | 同上 |

论文表 3 / 摘要目前的 Q2 数字是基线 A；正式实验（lowM、PR）用的是 B。必须二选一并全套统一。

### 2.2 真机任务

| 论文表 | 任务 ID | 输入/矩阵 | 返回向量 | PDF | 指标 |
|---|---|---|---|---|---|
| 表 10 基准组 k13 | `t20261128-003014-b_q2_baseline-be06017f` | in `0001ed…`；sub `be06017f…` | `experiments/tasks/…/raw/solutions.npz` | `B_Q2_baseline.pdf`（`af609f37…`） | `task_audit.json` |
| 表 10 罚项×3 | `t20261128-003124-b_q2_m3x-e2530a24` | in `0001ed…`；sub `e2530a24…` | 同上 | `B_Q2_m3x.pdf`（`f3173030…`） | 同上 |
| 表 10 规模缩减 k8 | `t20261128-003140-b_q2_k8-7be3225f` | in `0001ed…`；sub `7be3225f…` | 同上 | `B_Q2_k8.pdf`（`83ecc1b9…`） | 同上 |
| 表 9b 低M | `t20261128-043036-b_q2_k8_lowm-34f84ed6` | in `0001ed…`；sub `34f84ed6…` | 同上 | `B_Q2_k8_lowM.pdf`（`b570053d…`） | 同上 |
| 表 9b PR tp14 | `t20261128-161915-b_q2_k8_lowm_pr_tp14-d4f6e0ff` | in `0001ed…`；sub `d4f6e0ff…` | `raw/solutions_expanded.npz`（121 维）+ `raw/solutions.npz`（恢复 17 维） | `B_Q2_k8_lowM_PR_tp14.pdf`（`90365064…`） | `raw/result_metrics.json` + `task_audit.json` |

平台 ID / 设备 / 硬件时间：

| 任务 | 平台 ID | 设备 | 硬件 | 端到端 | 配额 |
|---|---|---|---|---:|---:|---:|
| baseline | `44923771c251417d91f15d9841651b4c` | SPQC-550 | 1.0327 ms | 7.790 s | 1 |
| m3x | `a8894d47ec774954ad2c0a3f99634eca` | SPQC-550 | 13.9135 ms | 7.657 s | 1 |
| k8 | `6258685cdb1c4541becdb1ae40fac598` | SPQC-550 | 10.9816 ms | 7.713 s | 1 |
| lowM | `b12121ad1655442e81c4a10de62199d1` | SPQC-1 | 4.3098 ms | 7.754 s | 1 |
| PR tp14 | `d833dedb390f4c54ac0c6d7db3bb9b11` | SPQC-550 | 1.5511 ms | 14.501 s | 1 |

## 3. Q3

### 3.1 预测最优（基线 B）

| 论文表 | 论文现状 | 正式 B 的实际值 | 来源 |
|---|---|---|---|
| 表 3 Q3 前 5 | PbTiO3、LaHfO2N、KNbO3、RbNbO3、KTiO2F | B 的 6 个并列最优：CsTaO3、KNbO3、PbTiO3、LaZrO2N、KTiO2F、NaTiO2F | `q3_audit.json` / `FINAL_METRICS.csv` |
| 表 8 O3 | PbTiO3，V̂<0.5 计数 24 | O3 原始最优 3 个：CsTaO3、KNbO3、PbTiO3；B 的 V̂<0.5 计数 **26** | 同上 |
| 表 8 NO2 | LaHfO2N，计数 5 | B 的 NO2 原始最优 **LaZrO2N**；计数 5 | 同上 |
| 表 8 FO2 | KTiO2F，计数 14 | FO2 原始最优 2 个：KTiO2F、NaTiO2F；B 的 V̂<0.5 计数 **16** | 同上 |
| 5.3 的 M/档数 | O3 97.8/2.27；NO2 58.2/1.87；FO2 73.3/1.99 | 全 52×52 的 M0 约为此值；实际提交是 topk13，M=89.941/56.875/73.170，resol_raw=2.2285/1.8584/1.9947，resol_adj=2.0/2.0/2.0 | 各任务 `config.json` |

表 8 的“V̂<0.5 计数”是全 52×52 口径；实际提交是 topk13，两者不可混写。O3 全量 24 vs 26、FO2 14 vs 16
的差异来自基线 A/B，不是 topk。

### 3.2 Q3 真机任务

| 切片 | 任务 ID | 平台 ID | 设备 | 输入矩阵 | 提交矩阵 | 返回向量 | PDF | 严格命中 |
|---|---|---|---|---|---|---|---|---|
| O3 | `t20261128-003159-b_q3_o3_baseline-7cd9ce6b` | `4a75fbffbe734857b87db54ed346c342` | SPQC-550 | `23908ae0…` | `7cd9ce6b…` | `raw/solutions.npz`（9×27） | `B_Q3_O3_baseline.pdf`（`bd1a7a10…`） | 0/9 |
| NO2 | **复用** `t20261128-003014-b_q2_baseline-be06017f` | `44923771c251417d91f15d9841651b4c` | SPQC-550 | `0001ed36…` | `be06017f…` | `raw/solutions.npz`（10×27） | `B_Q2_baseline.pdf`（`af609f37…`） | 0/10 |
| FO2 | `t20261128-003216-b_q3_fo2_baseline-ca295ce6` | `87d51d0a3fa14434a80d3bcb63878348` | SPQC-550 | `ef4f5e51…` | `ca295ce6…` | `raw/solutions.npz`（9×27） | `B_Q3_FO2_baseline.pdf`（`2a29b028…`） | 0/9 |

NO2 没有独立 Q3 任务：输入矩阵与 Q2 完全相同（`0001ed…`，2,704 个 V̂ 最大差 0），
所以只能复用 Q2 baseline，不能计为新的独立实验。

Q3 量化/全空间证据：

| 数字 | 文件 | 口径 |
|---|---|---|
| 全 52×52 原始最优 3/1/2 | `q3_audit.json` `per_x.*.raw_argmin_top` | 精确枚举 |
| topk13 保留全部 6 个 | `per_x.*.topk_raw_hits` / `topk_retains_all_raw_argmins` | 实际候选映射逐一核对；非无条件定理（并列截断反例见测试） |
| 量化全量合法最优 2/20/2 | `per_x.*.quantized_full_legal_set` | 2,704 合法指派 |
| 量化 topk13 合法最优 3/5/7 | `per_x.*.quantized_topk_legal_set` | 2,704 合法指派 |
| 全空间逻辑合法/非法间隙 24/36/36 | `per_x.*.submitted_space_exact` / `space_gap_audit.json` | 2^26 逻辑状态精确枚举；相对自旋 |

## 4. 论文表 → 证据文件速查

| 论文位置 | 应使用的证据 | 当前风险 |
|---|---|---|
| 摘要 / 表 2 / 表 3 Q1-Q3 数字 | `results/reproduction_20261127/final_answers.json`、`submission_q*.csv` | 现混用基线 A |
| 表 5 分辨率 | 各任务 `config.json`（resol_raw/resol_adj） | 全量与 topk 口径需注明 |
| 表 6 精度路线 | `precision_reducer/`、`d_precision_reducer.py`（PR5 离线） | “19 自旋”是教学例；动态范围 23.5→47 需核对 |
| 表 7 Q3 三种处理 | `CODEX_REVIEW_T004_RESPONSE.md` | 固定 X 是精确分解，不是单一 QUBO |
| 表 8 Q3 最优 | `q3_audit.json` | 现在用 A 的候选/计数；应为 B |
| 表 9b / 16 Q2 真机 | `task_audit.json` | 表 16 的样本数/硬件时间/F 值过期 |
| 表 10/16 首轮指标 | `task_audit.json` | best legal V / 排名与归档不符 |
| 表 12 成本 | `route_cost.json` + 任务 `task.json` | 配额“3 次”是历史值 |
| 附录 C 任务清单 | `experiments/registry.json` | 表 16 漏 Q3 两个任务 |
| Q3 真机（目前缺） | 本文件第 3.2 节 | 论文尚未写 Q3 硬件 |

## 5. 复现命令

```powershell
# Q3 证据与全空间间隙
$env:PYTHONPATH = "$PWD\code"
& "$env:LOCALAPPDATA\kaiwu-original\Scripts\python.exe" results\round2\T004_FINAL\EXPERIMENTS\q3_audit.py
& "$env:LOCALAPPDATA\kaiwu-original\Scripts\python.exe" results\round2\T004_FINAL\EXPERIMENTS\space_gap_audit.py
# 全部任务统一口径
& "$env:LOCALAPPDATA\kaiwu-original\Scripts\python.exe" results\round2\T004_FINAL\EXPERIMENTS\task_audit.py
# 成本
& "$env:LOCALAPPDATA\kaiwu-original\Scripts\python.exe" results\round2\T004_FINAL\EXPERIMENTS\route_cost.py
# 指标表
& "$env:LOCALAPPDATA\kaiwu-verify\Scripts\python.exe" results\round2\T004_FINAL\EXPERIMENTS\make_final_metrics.py
# 回归测试（50/50）
& "$env:LOCALAPPDATA\kaiwu-verify\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py"
```
