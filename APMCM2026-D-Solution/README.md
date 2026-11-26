# APMCM 2026 D 题 · 正式解题工作区

与 `APMCM2026-D-Feasibility/`（可行性预研）并列：那边回答的是"这套工具链能不能用"，这里放的是实际跑出来的代理模型、QUBO 编码、真机实验与论文底稿。

## 目录

| 目录 | 内容 |
|---|---|
| `statement/` | 赛题原文 PDF |
| `code/` | 全部脚本（9 个 .py + 公式源码 equations.tex） |
| `code/predictions/` | 代理模型对四个池子的全量预测（`pool_*_phys.csv` 为主线用的物理量路线） |
| `results/` | 指标表、验证集预测、真机任务统计、本地退火统计 |
| `results/vendor_reports/` | 平台导出的官方任务结果报告（PDF，含解向量与 Hamiltonian） |
| `results/cim_stats/`、`results/cim_samples/` | 各次真机任务的统计量与逐样本数据 |
| `results/logs/` | 训练与提交日志 |
| `figures/` | 论文用图（图 1–图 6）与平台演化图 |
| `paper/` | 论文底稿：英文版（docx + pdf）与中文版（docx + pdf） |
| `docs/` | 中文思路稿（名词解释、公式推导、实验设计） |

## 复现顺序

```bash
# 0. 一键全流程（数据核对 → 代理模型 → 三题求解 → 交付文件，约 30 秒）
python code/run_all.py
# 1. 数据准备：把赛题附件解压到 ../date/（8 个 csv）
# 2. 模型对照（表 2）
python code/model_compare.py
# 3. 问题 1：多任务训练 + 不确定性 + 论文插图
python code/train_q1.py
# 4. 最终代理模型（02+03 训练）→ 四个池子的 V̂
python code/final_surrogate_phys.py
# 5. QUBO 构造、穷举校验、8bit 精度分析（不消耗配额）
python code/d_submit_cim.py
# 6. 真机任务（需要 user_id / sdk_code，每次任务消耗 1 次配额）
python code/d_run_stats.py --task-name <name> --topk 13 --mode opt --mfactor 1
# 7. 本地退火对照（免费，用于统计合法率）
python code/local_sa_stats.py
```

## 关键结果

| 项目 | 数值 | 出处 |
|---|---|---|
| 代理模型（验证集，按元素对分组） | R² = 0.831，MAE = 2.59，Spearman = 0.934 | `results/model_compare.csv` |
| gap 两阶段 | R² 0.341 → 0.481，分类器 AUC 0.941 | `results/metrics.csv` |
| 问题 2 最优候选 | LaHfO₂N，V̂ = 0.0000（池内 2,704） | `code/predictions/pool_q2_phys.csv` |
| 问题 3 各 X 最优 | O3: PbTiO₃ / NO2: LaHfO₂N / FO2: KTiO₂F（均 V̂ = 0） | `code/predictions/pool_q3_phys.csv` |
| 全量 104 比特目标分辨率 | 0.51 档（低于量化噪声） | `results/cim_stats/` |
| 预筛 13×13（26 比特） | 2.00 档 | 同上 |
| 真机硬件求解时间 | 0.6673 ms / 次 | `results/vendor_reports/` |
| 本地退火合法率（3,000 次重启） | 50.6% / 51.9% / 51.1% | `results/local_sa_stats.csv` |

## 数据说明

赛题附件数据（`02/03/04/06/07/08/11/12_*.csv`，约 3 MB）不入库，请从赛题附件获取后放到 `../date/`。
`code/predictions/` 里的文件是代理模型的**输出**，不是原始数据，可直接复现 QUBO 与真机实验。

## 环境

Python 3.12 · numpy · pandas · scikit-learn · xgboost · lightgbm · mendeleev · `kaiwu==1.4.4`
（量子部分需要平台授权，见 `APMCM2026-D-Feasibility/docs/SDK_VERSION_REPORT.md`）

## 端到端复现结果（`code/run_all.py` 实测输出）

| 项目 | 结果 |
|---|---|
| 验证集（02→03，元素对不重叠） | R² 0.825 · MAE 2.576 · Spearman 0.934 · Top-100 命中 39/100 |
| 问题 2 | LaHfO₂N，V̂ = 0.0000；V̂<1 的 7 个 |
| 问题 3 | PbTiO₃（O₃），V̂ = 0.0000；V̂<1 的 73 个 |
| 子问题 13×13（26 比特） | 目标分辨率 1.87 档，模拟退火找回 V̂ = 0 |
| 全量 104 比特 | 目标分辨率 0.51 档（不可用，必须预筛） |

详见 `results/FINAL_ANSWERS.md`。

## 端到端复现结果（`code/run_all.py` 实测输出）

| 项目 | 结果 |
|---|---|
| 验证集（02→03，元素对不重叠） | R² 0.825 · MAE 2.576 · Spearman 0.934 · Top-100 命中 39/100 |
| 问题 2 | LaHfO₂N，V̂ = 0.0000；V̂<1 的 7 个 |
| 问题 3 | PbTiO₃（O₃），V̂ = 0.0000；V̂<1 的 73 个 |
| 子问题 13×13（26 比特） | 目标分辨率 1.87 档，模拟退火找回 V̂ = 0 |
| 全量 104 比特 | 目标分辨率 0.51 档（不可用，必须预筛） |

详见 `results/FINAL_ANSWERS.md`。

## 端到端复现结果（`code/run_all.py` 实测输出）

| 项目 | 结果 |
|---|---|
| 验证集（02→03，元素对不重叠） | R² 0.825 · MAE 2.576 · Spearman 0.934 · Top-100 命中 39/100 |
| 问题 2 | LaHfO₂N，V̂ = 0.0000；V̂<1 的 7 个 |
| 问题 3 | PbTiO₃（O₃），V̂ = 0.0000；V̂<1 的 73 个 |
| 子问题 13×13（26 比特） | 目标分辨率 1.87 档，模拟退火找回 V̂ = 0 |
| 全量 104 比特 | 目标分辨率 0.51 档（不可用，必须预筛） |

详见 `results/FINAL_ANSWERS.md`。

## 注意

仓库内**不含任何账号凭据**。license 由 `kaiwu.license.init(user_id, sdk_code)` 在本机生成，`sdk_code` 不要提交到仓库。
