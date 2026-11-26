# APMCM 2026 D 题 · 正式解题工作区

与 `APMCM2026-D-Feasibility/`（可行性预研）并列：那边回答的是"这套工具链能不能用"，这里放的是实际跑出来的代理模型、QUBO 编码、真机实验与论文底稿。

## 目录

| 目录 | 内容 |
|---|---|
| `statement/` | 赛题原文 PDF |
| `code/` | 全部脚本（15 个 .py：分析与求解脚本 + `paths.py` 路径配置 + `verify_project.py` 工程验收） |
| `code/predictions/` | 代理模型对四个池子的全量预测（`pool_*_phys.csv` 为主线用的物理量路线）与中间产物 |
| `results/` | 指标表、验证集预测、真机任务统计、本地退火统计 |
| `results/vendor_reports/` | 平台导出的官方任务结果报告（PDF，含解向量与 Hamiltonian） |
| `results/cim_stats/`、`results/cim_samples/` | 各次真机任务的统计量与逐样本数据 |
| `results/logs/` | 训练与提交日志 |
| `results/EXPERIMENT_INDEX.md` | 三次真机实验的索引（任务 ID、设备、时长、文件对应关系、MISSING 标记） |
| `results/ARTIFACT_SHA256.json` | 实验产物 SHA256 清单 |
| `figures/` | 论文用图（图 1–图 6）与平台演化图 |
| `paper/` | 论文底稿：英文版（docx + pdf）与中文版（docx + pdf） |
| `docs/` | 中文思路稿、工程验收记录、AI 使用记录 |
| `date/` | 赛题附件 CSV（不入库，需自行放置） |
| `models/` | 代理模型产物（`run_all.py` 生成，当前未入库） |

## 复现顺序

```bash
# 1. 数据准备：把赛题附件的 8 个 CSV 放到仓库根目录 date/
# 2. 一键全流程（数据核对 → 代理模型 → 三题求解 → 交付文件，约 30 秒）
python code/run_all.py
# 3. 模型对照（表 2）
python code/model_compare.py
# 4. 问题 1：多任务训练 + 不确定性 + 论文插图
python code/train_q1.py
# 5. 最终代理模型（02+03 训练）→ 四个池子的 V̂
python code/final_surrogate_phys.py
# 6. QUBO 构造、穷举校验、8bit 精度分析（不消耗配额）
python code/d_submit_cim.py
# 7. 真机统计：默认 dry-run，不创建云端任务、不消耗配额
python code/d_run_stats.py --task-name <name> --topk 13 --mode opt --mfactor 1
# 8. 确认要真机提交时，追加 --submit，并按提示逐字输入任务名完成二次确认
python code/d_run_stats.py --task-name <name> --topk 13 --mode opt --mfactor 1 --submit
# 9. 本地退火对照（免费，用于统计合法率）
python code/local_sa_stats.py
# 10. 工程验收（依赖 / 输入 / 入口 / 输出 / SHA256 / 路径 / dry-run）
python code/verify_project.py
```

所有脚本使用 `code/paths.py` 定位资源，路径相对仓库根目录解析，不依赖当前工作目录，也没有硬编码盘符。
缺失输入文件时会打印缺失清单并以非零码退出。

## 关键结果

| 项目 | 数值 | 出处 |
|---|---|---|
| 代理模型（验证集，按元素对分组） | R² = 0.831，MAE = 2.59，Spearman = 0.934 | `results/model_compare.csv` |
| gap 两阶段 | R² 0.341 → 0.481，分类器 AUC 0.941 | `results/metrics.csv` |
| 问题 2 最优候选 | LaHfO₂N，V̂ = 0.0000（池内 2,704） | `code/predictions/pool_q2_phys.csv` |
| 问题 3 各 X 最优 | O3: PbTiO₃ / NO2: LaHfO₂N / FO2: KTiO₂F（均 V̂ = 0） | `code/predictions/pool_q3_phys.csv` |
| 全量 104 比特目标分辨率 | 0.51 档（低于量化噪声） | `results/cim_stats/` |
| 预筛 13×13（26 比特） | 2.00 档（精度适配后矩阵口径；原始 Ising 矩阵口径 1.87 档） | `results/logs/` |
| 真机硬件求解时间 | 0.6673 / 0.9798 / 0.8221 ms（3 个任务，逐任务见 PDF） | `results/vendor_reports/` |
| 本地退火合法率（3,000 次重启） | 50.6% / 51.9% / 51.1% | `results/local_sa_stats.csv` |

## 数据说明

赛题附件数据（`02/03/04/06/07/08/11/12_*.csv`，约 3 MB）不入库，请从赛题附件获取后放到仓库根目录 `date/`。
`date/` 缺失时，`verify_project.py` 记为 BLOCKED，`run_all.py` 会打印缺失清单后退出。
`code/predictions/` 里的文件是代理模型的**输出**，不是原始数据，可直接复现 QUBO 与真机实验。

## 环境

Python 3.12 · numpy · pandas · scikit-learn · xgboost · mendeleev · `kaiwu==1.4.4`
（`lightgbm` 为 `model_compare.py` 的可选依赖；量子部分需要平台授权，见 `APMCM2026-D-Feasibility/docs/SDK_VERSION_REPORT.md`）

## 真机提交安全约定

- `d_run_stats.py` 默认 dry-run：只做本地建模与精度分析，不调用 license、不创建云端任务。
- 实际提交必须显式加 `--submit`，并在交互终端逐字输入任务名完成二次确认；非交互环境直接中止。
- `d_submit_cim.py --run` 同样需要二次确认。
- 授权只通过 `d_submit_cim.py --init` 的交互输入完成，不提供 `--user-id` / `--sdk-code` 参数。
- 设备型号由平台调度，SDK 不支持指定机型。

## 端到端复现结果（`code/run_all.py` 实测输出）

| 项目 | 结果 |
|---|---|
| 验证集（02→03，元素对不重叠） | R² 0.825 · MAE 2.576 · Spearman 0.934 · Top-100 命中 39/100 |
| 问题 2 | LaHfO₂N，V̂ = 0.0000；V̂<1 的 7 个 |
| 问题 3 | PbTiO₃（O₃），V̂ = 0.0000；V̂<1 的 73 个 |
| 子问题 13×13（26 比特） | 目标分辨率 1.87 档，模拟退火找回 V̂ = 0 |
| 全量 104 比特 | 目标分辨率 0.51 档（不可用，必须预筛） |

详见 `results/FINAL_ANSWERS.md`。

> 注：本节 R²=0.825 / Top-100 39 出自 `run_all.py` 的物理量路线；"关键结果"表中的 R²=0.831 出自 `model_compare.csv` 的直接回归路线，两者口径不同，不要混引。

## 工程验收与 AI 使用记录

- 工程验收记录：`docs/ENGINEERING_ACCEPTANCE.md`
- AI 使用记录：`docs/AI_USAGE_LOG.md`
- 真机实验索引：`results/EXPERIMENT_INDEX.md`

## 注意

仓库内**不含任何账号凭据**。license 由 `kaiwu.license.init(user_id, sdk_code)` 在本机交互生成，`sdk_code` 不要提交到仓库。
