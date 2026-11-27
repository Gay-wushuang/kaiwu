# 工程验收记录（独立复现环境）

- 首次记录：2026-11-27（Asia/Shanghai）
- 更新记录：2026-11-27，Phase 8 工程修复后（分支 `engineering/reproducibility`，PR #3）
- 冻结记录：2026-11-27，Phase 9 版本冻结（最终交付清单见 `RELEASE_CHECKLIST.md`）
- 验收对象：`Gay-wushuang/kaiwu` @ `db624f16af2ed28d9f11b59bfe0fb3950afb0ca6`
- 工作区状态：`main` 与 `origin/main` 一致；工程修复在独立分支进行，未改动 `main`
- 验收范围：环境、依赖、数据、真机记录完整性、提交安全审计、路径可移植性
- 不在范围内：数学模型、算法、参数与研究结论的修改
- 本次未提交任何真机任务，未消耗配额，未记录任何账号凭据

状态口径：`PASS` / `FAIL` / `BLOCKED` / `UNVERIFIED`。只以实际运行结果判定。

---

## 1. 本机环境状态

| 项目 | 实测值 | 判定 |
|---|---|---|
| 操作系统 | Windows 10 企业版 22H2，10.0.19045，x64 | PASS |
| CPU / 内存 | i5-12600KF（10C/16T）/ 63.8 GB（可用 30.4 GB） | PASS |
| 系统 Python | Anaconda 3.12.5（`E:\anaconda3`），未改动 | PASS |
| 独立复现环境 | `%LOCALAPPDATA%\kaiwu-verify`（CPython 3.12.6，新建，独立于队友环境） | PASS |
| 队友既有环境 | `APMCM2026-D-Feasibility\environment\.venv`（Python 3.12.6），未改动 | PASS |
| 仓库体积 | `APMCM2026-D-Solution` 17.1 MB / 130 文件；`APMCM2026-D-Feasibility` 0.5 MB / 34 文件 | PASS |

独立复现环境实测版本：

```text
kaiwu 1.4.4        kaiwu-community 1.0.8    numpy 2.5.5
pandas 2.2.3       scikit-learn 1.9.1        xgboost 3.4.1
mendeleev 1.4.0    scipy 1.18.1              joblib 1.6.0
matplotlib 3.10.3  lightgbm（未安装，仅影响表 2 的可选对照行）
```

说明：`lightgbm` 在 `model_compare.py` 中为可选依赖（缺失时打印提示并跳过），不阻塞主流程。

---

## 2. 依赖与数据完整性

### 2.1 代码依赖

| 项目 | 结果 | 判定 |
|---|---|---|
| 全部 15 个 `.py` 语法编译 | `compileall` 退出码 0 | PASS |
| 主流程依赖链（mendeleev / xgboost / joblib / kaiwu / scipy / sklearn） | 可导入并执行到数据读取步骤 | PASS |
| `d_submit_cim.py` 自检（不提交） | 正常运行，输出与队友日志同口径数值 | PASS |
| `local_sa_stats.py` 本地退火 | 运行完成，输出文件与仓库版本 **逐字节一致** | PASS |

本地退火复现结果（独立环境，3,000 次重启）：

| 配置 | 合法率 | H 最优 | H 中位 | 合法解最优 V* | 子问题内排名 |
|---|---|---|---|---|---|
| topk13_Mx1 | 50.6% | -2972 | -2992 | 0.0 | 1 |
| topk13_Mx3 | 51.9% | -3054 | -3110 | 0.0 | 1 |
| topk8_Mx1 | 51.1% | -1768 | -1784 | 0.0 | 1 |

四个结果 CSV 的 SHA256 与 `results/cim_samples/` 中同名文件完全一致，说明该路径具备确定性复现能力。

`d_submit_cim.py` 自检复现值（与 `results/logs/cim_run_k13.log` 对照）：

| 规模 | 比特 | 目标可分档数（本次） | 队友日志 | 判定 |
|---|---|---|---|---|
| 全量 52×52 | 104 | 0.51 | 0.51 | PASS |
| 预筛 26×26 | 52 | 0.95 | — | PASS（新增核对点） |
| 预筛 13×13 | 26 | 1.87 | 1.87 | PASS |
| 预筛 8×8 | 16 | 2.94 | 3.00（按精度适配后矩阵口径） | 口径差异，需统一 |

### 2.2 原始数据

2026-11-27 已从官方离线包接入 `date/`（来源：`E:\BaiduNetdiskDownload\2026 APMCM Problems\2026 APMCM Problem D\date`），
并按官方 `sha256_public.json` 校验通过。`date/` 已在 `.gitignore` 中排除，不入库。

| 文件 | 官方行数 | 实测行数 | 列数 | SHA256 | 判定 |
|---|---|---|---|---|---|
| 02_castelli_train.csv | 11,256 | 11,256 | 22 | 匹配 | PASS |
| 03_castelli_val.csv | 3,969 | 3,969 | 22 | 匹配 | PASS |
| 04_castelli_test_holdout.csv | 3,703 | 3,703 | 6 | 匹配 | PASS |
| 06_castelli_no_physics.csv | 15,225 | 15,225 | 6 | 匹配 | PASS |
| 07_castelli_q2_pool.csv | 2,704 | 2,704 | 6 | 匹配 | PASS |
| 08_castelli_q3_pool.csv | 8,112 | 8,112 | 6 | 匹配 | PASS |
| 11_castelli_q2_pool_blind.csv | 529 | 529 | 6 | 匹配 | PASS |
| 12_castelli_q3_pool_blind.csv | 1,587 | 1,587 | 6 | 匹配 | PASS |

补充核对：`02`、`03` 的 `V=0` 正例均为 0，符合官方说明的切分设计。

### 2.3 模型与交付文件

| 项目 | 结果 | 判定 |
|---|---|---|
| `code/predictions/pool_*_phys.csv`（4 个池） | 存在，表头 `id,formula,A,B,X,a_eq_b,V_hat` | PASS |
| `results/submission_q1_holdout.csv` | 3,703 行 × 6 列 | PASS |
| `results/submission_q2_top20.csv` | 20 行 × 6 列 | PASS |
| `results/submission_q3_top20.csv` | 20 行 × 6 列 | PASS |
| `results/final_answers.json` / `FINAL_ANSWERS.md` | 存在且可解析 | PASS |
| `results/val_predictions.csv` | 3,969 行 × 9 列 | PASS |
| `models/surrogate_phys.joblib` | 仓库未入库；临时副本已成功生成 | PASS（可复现，不入库） |
| 论文 PDF | 中文版/彩色版各 22 页，草稿版各 21 页，可正常解析 | PASS（格式合规见第 11 节） |
| 赛题原文 PDF | 存在 | PASS |

---

## 3. 真机授权状态

| 项目 | 实测 | 判定 |
|---|---|---|
| 本机 license 文件 | 已通过 `--init` 交互生成（凭据未落盘、未记录） | PASS |
| `BruteForceOptimizer` / `TabuSearchOptimizer` | 可运行 | PASS（免授权） |
| `SimulatedAnnealingOptimizer` | 本次未复测（license 已通过 27 比特校验） | UNVERIFIED |
| `CIMOptimizer` 签名 | `(task_name, wait=False, interval=6, project_no=None, task_mode='optimization', sample_number=10)`，与 SDK 1.4.4 文档一致 | PASS |

授权需由账号持有人在本机交互输入，建议命令：

```powershell
& "$env:LOCALAPPDATA\kaiwu-verify\Scripts\python.exe" APMCM2026-D-Solution\code\d_submit_cim.py --init
```

该命令使用 `input` + `getpass` 交互读取，凭据不落盘、不进命令行历史。
Phase 8 已移除 `--user-id` / `--sdk-code` 命令行参数入口，授权只能走上述交互方式。

未验证项：账号剩余配额、可用机型、配额有效期。均需登录平台查看，标记 UNVERIFIED。

---

## 4. 已有真机实验记录清单

### 4.1 成功任务（3 个，各消耗 1 次优化配额）

| 任务名 | 任务 ID | 量子计算机 | 提交/结束 | 硬件时长 | 样本/合法 | 报告 | 统计 | 逐样本 | 日志 |
|---|---|---|---|---|---|---|---|---|---|
| apmcm_q2_no2_k13 | `4cc56fdeb17d4fdc95cbdd1d436ffeef` | SPQC-550 | 14:11:16 / 14:11:28 | 0.6673 ms | 7 / 2 | ✓ PDF | ✗ | ✗ | ✓ `cim_run_k13.log` |
| apmcm_q2_k13_m3x | `fa769c1bf4974f5594c357ada1bf4d5a` | SPQC-550 | 14:40:12 / 14:40:16 | 0.9798 ms | 10 / 1 | ✓ PDF | ✓ | ✓ | ✓ 两份日志 |
| apmcm_q2_k8_m1x | `3d77a22670424dc7be3ff1872e2db416` | SPQC-1000 | 14:47:39 / 14:47:43 | 0.8221 ms | 10 / 1 | ✓ PDF | ✓ | ✓ | ✓ `run_k8.log` |

任务 ID、时间、硬件时长均取自 `results/vendor_reports/*.pdf` 原文；样本数与合法数由 PDF 解向量与 `_stats.json` 交叉核对一致。

### 4.2 未成功的提交

| 任务名 | 结果 | 证据 |
|---|---|---|
| apmcm_q2_k13_samp200 | 任务创建失败：采样模式配额不足，未生成任务、未消耗配额 | `results/logs/run_samp200.log` |
| apmcm_q2_k13_m3x（首次） | 任务已完成，但结果下载时 SSL 中断；重跑同名同矩阵任务复用服务端结果，未新建任务 | `run_m3x.log`、`run_m3x_retry.log`（重试日志无 "Task submit" 行） |

### 4.3 记录对应关系缺口

1. `apmcm_q2_no2_k13` 缺 `_stats.json`、`_samples.csv`、`apmcm_q2_no2_k13_result.csv`；现有逐样本信息只存在于日志文本和人工整理的 `results/official_task_report.csv`。
2. `official_task_report.csv` 含 "1个/0个" 等中文字段，属人工转录而非原始导出，已与 PDF 对照确认数值一致，但缺少生成脚本。
3. 平台导出的 `.pkl` 结果文件（PDF 中引用的文件名）未入库。
4. 无统一的"任务 ID ↔ 文件 ↔ 日志"清单文件，本节表格为首次建立。

---

## 5. 提交路径安全审计

全仓库无 CI、无批处理、无定时任务、无 import 时自动提交的代码路径。

| 脚本 | 触发条件 | 风险 | 判定 |
|---|---|---|---|
| `d_submit_cim.py` | 无参数时仅做精度自检；`--run` 才构造 `CIMOptimizer` 并提交 | 显式开关，默认安全 | PASS（默认）/ 需人工授权（`--run`） |
| `d_run_stats.py` | 默认 dry-run；`--submit` 才提交，且需逐字输入任务名二次确认；非交互终端直接中止 | 已加固 | PASS（Phase 8） |
| `run_all.py` | 不调用任何真机接口 | 无 | PASS |
| `local_sa_stats.py` | 仅本地退火 | 无 | PASS |

两道被动保护：未授权时 `verify_license` 会要求输入账号；`d_submit_cim.py` 在分辨率 < 1 时主动中止（除非 `--force`）。

凭据卫生：全仓库未检索到 `sdk_code`/`user_id`/Token 明文；无凭据类文件被 Git 跟踪。

---

## 6. 尚未完成的工程任务

按优先级：

1. **补齐 `date/` 原始数据**（8 个 CSV，行数见 2.2）。这是问题 1 与端到端复现的唯一硬阻塞。
2. **统一数据目录约定**：`d_submit_cim.py`/`d_run_stats.py` 读取 `code/pool_q2_phys.csv`，但仓库文件在 `code/predictions/`；`run_all.py` 又写回 `code/` 根目录。当前直接按 README 第 5、6 步执行会 `FileNotFoundError`（已实测）。
3. **移除硬编码绝对路径**：`d_check.py`、`d_baseline.py`、`d_route_compare.py`、`d_step12.py`、`d_step3.py`、`final_surrogate.py`、`final_surrogate_phys.py`、`model_compare.py`、`run_all.py`、`train_q1.py`、`local_sa_stats.py` 均写死 `D:\比赛\...` 或 `D:\temp\...`，在本机无法运行。
4. **补 `apmcm_q2_no2_k13` 的统计与逐样本文件**：建议用 PDF 中的 7 个解向量与 `code/predictions/pool_q2_phys.csv` 重算并落盘，附生成脚本。
5. **建立真机任务清单文件**（建议 JSON/CSV）：任务名、任务 ID、机型、矩阵规模、时间、时长、消耗配额、关联文件。
6. **补充模型产物**：`models/surrogate_phys.joblib` 未入库；若要求离线复现，需在补齐数据后生成并决定是否纳入版本管理。
7. **文档一致性修正**：`README.md` 末尾"端到端复现结果"整节重复 3 次；`code/` 实际 13 个 `.py` 而非 9 个。
8. **提交安全加固**（工程层面，建议不改变算法）：给 `d_run_stats.py` 增加 `--dry-run` 默认值或二次确认；移除 `--user-id/--sdk-code` 命令行参数入口。

### 6.1 Phase 8 处理结果

| # | 任务 | 状态 | 说明 |
|---|---|---|---|
| 1 | 补齐 `date/` | DONE | 官方 8 个 CSV 已接入并通过 SHA256 校验 |
| 2 | 统一 `code/predictions/` 读取路径 | DONE | `d_submit_cim.py`、`d_run_stats.py`、`run_all.py`、`final_surrogate*.py` 已统一 |
| 3 | 移除硬编码绝对路径 | DONE | 新增 `code/paths.py`，11 个脚本改造完成 |
| 4 | 补 `apmcm_q2_no2_k13` 统计/逐样本 | 未做 | 按约束不补造；`results/EXPERIMENT_INDEX.md` 标记 MISSING |
| 5 | 真机任务清单 | DONE | `results/EXPERIMENT_INDEX.md` |
| 6 | 模型产物 `joblib` | DONE | 临时副本已生成；仓库按 `.gitignore` 不入库 |
| 7 | README 修正 | DONE | 删除重复章节，脚本数 9 → 15 |
| 8 | 提交安全加固 | DONE | dry-run 默认 + 二次确认 + 移除凭据参数 |

---

## 7. 需要人工确认的事项

1. **论文与原始记录的数字口径**（不修改研究结论，仅提请确认）：
   - 论文表 15 三行"硬件时间"均为 0.6673 ms，而三份 PDF 分别为 0.6673 / 0.9798 / 0.8221 ms。
   - 论文正文称三组实验均在 SPQC-550 上完成，但 `apmcm_q2_k8_m1x` 的 PDF 标注为 SPQC-1000。
   - 论文附录 C 称"下载失败后没有重试"，但仓库存在 `run_m3x_retry.log`；该重试复用服务端结果、未新建任务，建议改为"未重新提交任务"。
   - "13×13 预筛 2.00 档"与 `cim_run_k13.log` 的 1.87 档来自两套计算口径（精度适配后矩阵 vs 原始 Ising 矩阵），需在正文注明口径。
   - `README` 中 R²=0.831/MAE=2.59 出自 `model_compare.csv`（直接预测 V），R²=0.825/Top-100 39 出自 `run_all.py`（物理量路线），二者不可混引。
2. **配额归属与余额**：队友账号已用 3 次优化配额，采样配额为 0。用户本人账号已领取的配额数量、机型、有效期需登录平台确认；本记录无法验证。
3. **是否允许提交新真机任务**：本阶段按约束未提交。后续任何提交需人工明确授权任务数、比特规模与预计消耗。
4. **原始数据**：已从官方离线包接入并通过 SHA256 校验；已加入 `.gitignore`，不入库。是否需要在队内共享另行决定。
5. **论文提交合规**：英文版、文件名、页眉、承诺书签名、支撑材料打包需由队员在提交前完成（见第 12 节）。
6. **竞赛指定 SDK 版本**：仍为 BLOCKED（竞赛页需登录）。当前锁定 `kaiwu==1.4.4` 仅代表本地可复现。

---

## 8. 本次验收使用的命令与结果摘要

```powershell
# 1. 代码同步与状态
git fetch --all --prune; git status -sb        # 已是最新，工作区干净

# 2. 独立环境（新建，不改动队友环境）
python -m venv %LOCALAPPDATA%\kaiwu-verify
pip install kaiwu==1.4.4 pandas==2.2.3 scikit-learn xgboost mendeleev scipy joblib matplotlib

# 3. 语法与依赖
python -m compileall -q <临时副本>\code        # 退出码 0

# 4. 精度自检（不提交、不耗配额）
python <临时副本>\code\d_submit_cim.py          # 0.51 / 0.95 / 1.87 / 2.94 档

# 5. 本地退火对照
python <临时副本>\code\local_sa_stats.py        # 50.6% / 51.9% / 51.1%，输出逐字节一致

# 6. license 探测（stdin 关闭，不输入凭据）
python -c "..."                                # SAOptimizer = BLOCKED_LICENSE
```

复现时所有写操作均在 `%TEMP%\apmcm_verify` 临时副本中完成，仓库文件未被修改。

---

## 9. 合规声明

- 未提交真机任务，未消耗任何配额。
- 未记录、未打印、未提交任何账号、密码、`sdk_code` 或 Token。
- 未修改队友的模型、算法、参数、结果文件与研究结论。
- 本记录仅覆盖环境、依赖、数据、记录完整性与提交安全；所有结论可回溯到上述命令输出与仓库文件。

---

## 10. Phase 8 修复记录（2026-11-27）

### 10.1 修复前后对照

| 项目 | 修复前 | 修复后 | 状态 |
|---|---|---|---|
| 资源路径 | 11 个脚本写死 `D:\比赛\...` / `D:\temp\...` | 统一 `code/paths.py`，`pathlib` + 仓库根相对路径 | PASS |
| 池子预测读取 | `d_submit_cim.py` 读 `code/pool_q2_phys.csv`（实际不在该目录） | 统一读 `code/predictions/` | PASS |
| 输出目录 | 部分脚本写 `D:\temp\`；统计/逐样本与仓库归档目录不一致 | 统一写 `results/`、`results/cim_stats/`、`results/cim_samples/`、`code/predictions/` | PASS |
| 缺失输入 | 直接抛 pandas `FileNotFoundError` | 打印缺失清单 + 放置目录，非零码退出 | PASS |
| `d_run_stats.py` 提交 | 带 `--task-name` 即提交 | 默认 dry-run；`--submit` + 逐字输入任务名二次确认 | PASS |
| `d_submit_cim.py --run` | 直接提交 | 提交前二次确认 | PASS |
| 凭据入口 | `--user-id` / `--sdk-code` 可写入命令行历史 | 参数已移除，仅交互 `input` + `getpass` | PASS |
| README | "端到端复现结果"重复 3 次；脚本数写 9（实际 13） | 重复删除；脚本数改为 15 | PASS |
| 真机记录索引 | 无 | `results/EXPERIMENT_INDEX.md`（3 个任务 + 1 次失败提交，缺失标 MISSING） | PASS |
| 产物哈希 | 无 | `results/ARTIFACT_SHA256.json`（43 个文件） | PASS |
| 工程自检 | 无 | `code/verify_project.py`（8 类检查） | PASS |

### 10.2 Phase 8 验收输出（`python code/verify_project.py`）

```text
[1] 依赖完整性        9/9 必需依赖 OK；lightgbm 未安装（可选）
[2] 输入数据          8/8 存在，SHA256 与官方清单一致
[3] 预测文件          4/4 OK；models/surrogate_phys.joblib 未入库 → BLOCKED（临时副本可生成）
[4] 程序入口          15 个脚本语法检查通过
[5] 路径可移植性      未发现盘符绝对路径或 sys.path 注入
[6] 输出文件          10/10 存在，行数符合预期
[7] dry-run 安全性    退出码 0；含 [DRY-RUN]；未触发 license 输入
[8] SHA256 校验       43/43 一致
结论：PASS 15 | FAIL 0 | BLOCKED 1 | WARN 1
```

### 10.3 安全验证证据

| 验证 | 命令 | 结果 |
|---|---|---|
| dry-run 不建任务 | `d_run_stats.py --task-name verify_dryrun --topk 13 --mode opt --dry-run` | 输出 `[DRY-RUN] 未创建云端任务`，退出码 0 |
| 非交互提交拦截 | `d_run_stats.py ... --submit` + 关闭 stdin | 二次确认处 `[中止] 当前不是交互终端`，未进入 license |
| 确认文本校验 | 单元调用 `confirm_submit`，先输入错误任务名再输入正确任务名 | `False` → `True`，逻辑符合预期 |
| 凭据扫描 | 工作区全文 + Git 历史检索 `sdk_code` / `user_id` / `password` / `token` | 未发现明文凭据；历史提交仅出现参数名与文档字样，无凭据值 |
| 本地退火复跑 | 临时副本执行 `local_sa_stats.py`（3,000 次重启） | 4 个结果 CSV 与仓库版本 SHA256 一致 |

### 10.4 未关闭项

1. `models/surrogate_phys.joblib` 未入库（按 `.gitignore` 排除；临时副本已验证可生成）。
2. `apmcm_q2_no2_k13` 的统计/逐样本/结果 CSV MISSING（按约束不补造）。
3. 论文表 15 的硬件时长与机型口径差异待队员确认（见第 7 节）。
4. 论文提交规范存在多项不合规，见第 11 节。

---

## 11. 端到端复现结果差异（2026-11-27）

原始数据接入后，在临时副本 `%TEMP%\apmcm_e2e` 执行 `python code/run_all.py`，全流程 74.0 s 成功完成。
仓库既有结果未被覆盖。复现值与仓库记录**接近但不完全一致**，按约束只报告差异，不调整算法、参数或随机种子。

| 项目 | 仓库记录 | 本次复现 | 差异 |
|---|---|---|---|
| 验证集 R² | 0.824818 | 0.824836 | +0.000018 |
| 验证集 MAE | 2.575652 | 2.571641 | -0.004011 |
| 验证集 RMSE | 4.597437 | 4.597198 | -0.000239 |
| Spearman | 0.933916 | 0.935325 | +0.001409 |
| Top-100 命中 | 39 | 40 | +1 |
| 问题 2 首位 | LaHfO₂N | LaZrO₂N | 候选变化（两者 V̂ 均为 0） |
| 问题 2 V̂<1 数量 | 7 | 6 | -1 |
| 问题 3 首位 | PbTiO₃ | PbTiO₃ | 一致 |
| 问题 3 V̂<1 数量 | 73 | 68 | -5 |
| 13×13 目标分辨率 | 1.87 档 | 1.86 档 | -0.01 |
| 3 个提交 CSV | — | — | SHA256 全部不同 |
| 四个池的 V̂ | — | — | 平均绝对差约 0.31，最大 4.73 |

差异定位（未做算法调整）：

1. 仓库未锁定 `xgboost` / `scikit-learn` / `mendeleev` 的具体版本，README 只列包名；本次环境为 `xgboost 3.4.1`、`scikit-learn 1.9.1`、`mendeleev 1.4.0`，与队友当时的 `D:\Python` 环境版本无法核对。
2. 本次环境未安装 `lightgbm`，`model_compare.py` 少一行可选对照（不影响 `run_all.py` 主流程）。
3. 代理模型对候选的 V̂ 排序在 0 附近高度敏感，指标几乎相同但首位候选改变，属于版本/数值差异而非流程错误。

建议（需队员决定）：补充锁定依赖版本（`requirements.lock`）后再做一次端到端复现，把差异收敛到 0 或明确记录可接受范围。本次未擅自安装或降级依赖。

---

## 12. 论文提交规范核对（2026 APMCM）

规范来源：`E:\BaiduNetdiskDownload\2026 APMCM Problems\2026 APMCM 论文提交规范、论文模板、承诺书\2026 APMCM Essay format and submission specifications.pdf`。

| 规范要求 | 现状 | 判定 |
|---|---|---|
| 论文必须用英文，正文与图表不得出现中文 | `APMCM_D_paper_CN.pdf` 含 10,564 个中文字符，页眉亦为中文 | **FAIL** |
| 首页为摘要页，第二页为目录页 | 首页为中文摘要，第二页为目录 | 结构 PASS / 语言 FAIL |
| 页眉只含队号与页码，英文格式 | `TeamDapmcm26306844 第1 页/ 共22 页` | **FAIL**（中文页码格式） |
| 正文不超过 25 页 | 全文 22 页 | PASS |
| 字号 11 或 12 | 需人工确认 | UNVERIFIED |
| 论文文件名 `#***.pdf` | 现有 `APMCM_D_paper_CN.pdf` 等 | **FAIL**（应为 `Dapmcm26306844.pdf`） |
| 承诺书 `#***cns.pdf` 或 `.jpg`，需全员签名 | 仓库无承诺书文件 | **FAIL**（缺失） |
| 支撑材料 `#***fj.zip` 或 `.rar` | 仓库无打包文件 | **FAIL**（缺失） |
| 附录给出软件名称与全部源码 | 有软件清单与 2 段核心代码，其余指向支撑材料 | **FAIL**（不满足“全部源码”） |
| 参考文献格式 | 已有参考文献，格式需人工逐条核对 | UNVERIFIED |

说明：论文语言与命名属于正式提交材料，需由参赛队员自行翻译、排版、签名并打包；AI 未改写论文正文或研究结论。
建议最终文件名：`Dapmcm26306844.pdf`、`Dapmcm26306844cns.pdf`、`Dapmcm26306844fj.zip`。

---

## 13. Phase 9 版本冻结记录（2026-11-27）

| 项目 | 结果 |
|---|---|
| 代码冻结 | 分支 `engineering/reproducibility`，PR #3 OPEN，未合并 |
| 官方数据 | 8/8 CSV 通过官方 SHA256 与行数校验 |
| 本机依赖锁定 | `requirements.lock.txt`（CPython 3.12.6，54 个包） |
| 原始环境依赖清单 | BLOCKED：队友未提供完整清单 |
| 实验版本清单 | `results/EXPERIMENT_VERSION.json`（代码 SHA、数据 SHA、依赖、种子、产物哈希、真机任务 ID） |
| 原始实验归档 | `results/`（冻结，未覆盖） |
| 独立复现归档 | `results/reproduction_20261127/`（单独目录，未覆盖原始结果） |
| 最终工程自检 | PASS 15 / FAIL 0 / BLOCKED 0 / WARN 1（lightgbm 可选未装） |
| 真机 License | PASS（`verify_license(27)` 通过；未提交任务、未消耗配额） |
| 真机任务 | 本阶段 0 次提交、0 配额消耗 |
| 最终交付清单 | `RELEASE_CHECKLIST.md` |

未解决与需人工处理事项见 `RELEASE_CHECKLIST.md`。
