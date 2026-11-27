# Phase 10：正式实验执行工程（审计、实现与测试记录）

- 时间：2026-11-27（Asia/Shanghai）
- 分支：`engineering/reproducibility`
- 基线：PR #3（head `ddc9635`，base `main`）
- 边界：未提交任何真机任务，未消耗配额，未保存任何凭据；未修改模型、算法、参数、QUBO 系数与科学结论
- 状态口径：`PASS` / `FAIL` / `BLOCKED` / `UNVERIFIED`

---

## 0. 结论摘要

| 项目 | 状态 | 说明 |
|---|---|---|
| 现有工程审计 | PASS | 分支、PR、脚本数据流、真机返回格式已核对 |
| 数学口径一致性 | **FAIL（仅记录）** | 发现 2 处口径不一致，按约束未修改，交队员核验（见 2.4） |
| 实验输入版本管理 | PASS | 新增登记/冻结/SHA256/来源隔离，9 项测试通过 |
| 真机任务管理 | PASS（模拟验证） | dry-run 默认、配额账本、去重、逐任务确认、状态与恢复 |
| 实验归档 | PASS | 每任务独立目录，原始返回与元数据完整 |
| 真机端到端提交 | BLOCKED | 按约束未提交；失败阶段判定基于 SDK 报错文本与历史日志 |
| PR #3 合并 | 待人工决定 | 可合并（CLEAN），但无评审、无 CI，且有 CLI 行为变化 |

---

## 1. P0 现有工程审计

### 1.1 分支与 PR

| 项目 | 实测 |
|---|---|
| 本地分支 | `engineering/reproducibility`，工作区干净，与 origin 同步 |
| main 与分支关系 | `main` 是分支祖先，分支领先 5 个提交（快进可合并） |
| PR #3 | OPEN，MERGEABLE，mergeStateStatus=CLEAN，31 文件，+5575 / −236 |
| 评审 | 0 条 review、0 条 comment |
| CI | 无 status checks |
| 变更范围 | 路径可移植性、dry-run 安全加固、实验索引与哈希清单、文档 |

### 1.2 正式研究脚本数据流

| 脚本 | 输入 | 输出 | 被谁调用 |
|---|---|---|---|
| `run_all.py` | `date/` 8 个官方 CSV | `code/predictions/pool_*_phys.csv`、`results/submission_*.csv`、`models/surrogate_phys.joblib`、`results/final_answers.json` | 手工入口 |
| `train_q1.py` / `final_surrogate*.py` / `model_compare.py` | `date/` CSV | `code/predictions/*`、`results/metrics.*` | 手工入口 |
| `d_step12.py` / `d_step3.py` | `date/` + `code/predictions/` | 对照输出、`qubo_q2.npz` | 手工入口 |
| `d_submit_cim.py` | `code/predictions/pool_q2_phys.csv` | 自检：终端；`--run`：`results/cim_tasks/` 检查点 + `results/<task>_result.csv` | 手工入口 |
| `d_run_stats.py` | 同上 | `results/cim_stats/*.json`、`results/cim_samples/*.csv`、`figures/*_H_hist.png` | 手工入口 |
| `local_sa_stats.py` | 同上 | `results/local_sa_stats.csv`、`results/cim_samples/local_sa_*.csv` | 手工入口 |
| `verify_project.py` | 全部 | 终端（8 类检查） | 手工入口 |

关键缺口：`d_submit_cim.load_pool()` 写死文件名 `pool_q2_phys.csv`，且只能读固定列 `A/B/V_hat`；没有任何入口可以接收队员另存的矩阵或变量映射。

### 1.3 真机返回格式（SDK 1.4.4 实测）

| 事实 | 证据 |
|---|---|
| QUBO `n` 比特 → Ising `n+1` 比特，辅助自旋位于**末位** | `kw.core.qubo_matrix_to_ising_matrix` 源码；3×3 实测得到 4×4 |
| Ising 矩阵对称；返回值为 `-ising_mat` 与 bias | 源码；`np.allclose(I, I.T)=True` |
| 能量约定 `H = -sᵀJs` | `kw.common.hamiltonian` 源码；实测与自算一致（0.625） |
| `solve()` 返回二维 `int8` 解矩阵（样本 × Ising 比特） | SDK docstring；历史日志 `形状 (7, 27)`、`10 × 27` |
| 任务身份 = `task_name` + 矩阵哈希 | SDK docstring；`_ising_to_md5_hash` 可用 |
| 有查询接口 `get_task_result(ising_matrix)`，不会新建任务 | `inspect.signature` 实测 |
| 设备不可指定，由平台调度 | SDK 文档与 README 既有约定 |

### 1.4 数学正确性口径问题（只记录，未修改）

#### 问题 A：Hamiltonian 方向标注与排序方向不一致

- SDK 与代码均使用 `H = -sᵀJs`，且实测满足 `QUBO 值 = H + bias`（3 变量样例：0.625 + (−0.625) = −0.5）。因此 **H 越小越好**。
- 但 `d_run_stats.py` 第 98 行按 `H` 降序写出样本 CSV，图注写“Hamiltonian（越大越好，按 QBoson 约定）”。
- 两份真机逐样本文件给出反证：

| 任务 | 唯一合法解的 H | 其余非法解的 H 范围 |
|---|---:|---|
| `apmcm_q2_k13_m3x` | **−3126** | −3086 … 8930 |
| `apmcm_q2_k8_m1x` | **−1796** | −1732 … 3228 |

即最优/合法解位于 H 最小端。该不一致只影响样本排序与图注，`best_V`、`valid_rate` 等统计按全体样本独立计算，未改变既有结论；但图注与排序会误导读者。

#### 问题 B：模拟退火 ΔH 系数为真实值的一半

- 令 `H = -sᵀJs`、`J` 对称。翻转自旋 `i` 的精确能量差为
  `ΔH = 4·s_i·(Js)_i − 4·J_ii`。
- `local_sa_stats.py` 第 36 行与 `run_all.py` 第 186 行均写为
  `dH = 2·s_i·(Js)_i − 2·J_ii`，即 `ΔH/2`。
- 后果：Metropolis 接受概率实际为 `exp(−ΔH/(2T))`，等效温度翻倍。目标函数、精确枚举结果与最终最优值不受影响，但退火轨迹与“温度”解释不一致，可能影响 3,000 次重启的统计行为。

#### 问题 C：按数组位置解码，而不是按变量名

- 当前构造没有松弛变量，`[:nA+nB]` 截断可用；辅助自旋确实在末位。
- 但预研仓库 `AGENTS.md` 的约定是“按变量名读取，不按数组位置（约束会自动插入松弛变量）”。若后续改用 SDK 的 `QuboModel` / 带约束建模，位置截断会静默错位。

#### 问题 D：分辨率双口径（已在文档中记录）

- 原始 Ising 矩阵口径 1.87 档；8bit 精度适配后矩阵口径 2.00 档。
- 新入口 `plan` 同时打印两种口径，未替任何一方背书。

### 1.5 对团队模型产物的接入能力

结论：**原有入口不具备通用接入能力**。具体限制：

1. 文件名写死为 `pool_q2_phys.csv`，无法选择版本。
2. 只接受长表 `A/B/V_hat`，不接受已筛好的矩阵文件。
3. 没有变量映射文件，也没有输入哈希记录。
4. 没有区分“原始预测”与“独立复现”产物，存在混用风险。
5. 运行结果直接写 `results/`，没有任务级隔离，无法保证不覆盖。

---

## 2. 工程实现

### 2.1 新增文件

| 文件 | 作用 |
|---|---|
| `code/experiment_input.py` | 输入版本登记、冻结、SHA256、来源隔离、加载校验 |
| `code/experiment_archive.py` | 任务归档目录、本地注册表、原始结果保存、报告归档 |
| `code/experiment_budget.py` | 本地配额账本与提交前预算检查 |
| `code/mock_backend.py` | 离线模拟后端，可注入 submit/run/download 失败 |
| `code/d_experiment.py` | 统一 CLI：inputs / plan / run / status / resume / attach-report / budget |
| `tests/test_experiment_pipeline.py` | 9 项自动化测试（教学矩阵 + 模拟后端） |
| `docs/PHASE10_REPORT.md` | 本文件 |

### 2.2 未改动的既有文件

`run_all.py`、`train_q1.py`、`final_surrogate*.py`、`model_compare.py`、`d_step12.py`、`d_step3.py`、`d_submit_cim.py`、`d_run_stats.py`、`local_sa_stats.py`、`verify_project.py` 均未改动，避免影响既有复现命令与论文数字。

### 2.3 输入版本规范

```
experiments/inputs/<version>/
  manifest.json          # kind、shape、matrix_sha256、文件 SHA256
  matrix.csv             # 冻结的带标签矩阵
  mapping.json           # 子问、X 取值、数值列名、优劣方向
  source_manifest.json   # 原始路径、格式与过滤条件
```

规则：

1. 版本名唯一，已登记版本**拒绝覆盖**；改动输入必须登记新版本。
2. 加载时逐文件复核 SHA256，任一不一致即拒绝运行。
3. 来源类型：`team_model` / `official_prediction` / `independent_reproduction` / `teaching`。
4. 声明为原始预测或独立复现时，路径特征必须匹配；不匹配直接拒绝。
5. 长表登记时若存在重复 `(A,B)`、缺失值或 X 过滤后为空，直接拒绝，不代为填充。

### 2.4 任务归档结构

```
experiments/tasks/<task_id>/
  task.json              # 状态、任务名、输入哈希、提交矩阵哈希、设备、错误阶段
  config.json            # 参数、Git commit/branch/dirty、SDK/Python 版本、配额单位
  input/                 # matrix.csv、mapping.json、manifest.json、ising_matrix.csv、hashes.json
  raw/                   # solutions.npz、solutions.csv、solution_energy.csv、platform_result.json
  logs/run.log           # 运行日志
  attempts.jsonl         # 每次提交/恢复的阶段记录
  reports/               # 平台导出的 PDF（人工 attach）
  sdk_checkpoints/       # SDK 断点（不提交到 Git）
```

- `task_id` 形如 `t20261127-104735-q2_k13-585e509f`，前 8 位为实际提交矩阵哈希。
- 同一目录内原始解、平台结果均**拒绝覆盖**。
- 只保存原始向量与机械能量 `H=-sᵀJs`，不解析化学式、不计算 V̂、不形成任何科学结论。

### 2.5 提交安全与配额

| 能力 | 实现 |
|---|---|
| dry-run 默认 | `run` 不带 `--submit` 只打印计划，不写归档、不联网 |
| 人工逐任务确认 | 必须逐字输入完整 `task_id`；非 TTY 直接中止 |
| 配额预算 | `experiments/config/quota_budget.json` 本地账本，提交前检查剩余 |
| 重复拦截 | 同任务名+同矩阵阻断；同矩阵换名需显式 `--allow-matrix-reuse` |
| 失败阶段区分 | `submit_failed` / `run_failed` / `download_failed` / `unknown` |
| 结果恢复 | `resume` 只调用 `get_task_result`，绝不重新提交 |
| 设备 | 不提供选择参数；`device` 仅从平台报告人工归档 |
| 凭据 | 不接收命令行凭据；归档时过滤 `authorization/sdk_code/user_id/token/password` |

---

## 3. 测试记录

### 3.1 自动化测试（教学矩阵 + 模拟后端）

命令：

```powershell
cd APMCM2026-D-Solution
& "$env:LOCALAPPDATA\kaiwu-verify\Scripts\python.exe" -m unittest discover -s tests -v
```

结果：`Ran 9 tests in 1.981s — OK`

| # | 用例 | 验证内容 | 结果 |
|---|---|---|---|
| 1 | `test_input_version_isolation_and_tamper_detection` | 版本隔离、篡改检测 | PASS |
| 2 | `test_mixed_kind_refused` | 原始预测/独立复现不得混用 | PASS |
| 3 | `test_dry_run_no_files_no_network` | 断网条件下 dry-run 成功、不建归档 | PASS |
| 4 | `test_quota_protection_blocks_before_submit` | 预算为 0 时提交前中止 | PASS |
| 5 | `test_duplicate_submission_blocked` | 同任务名/同矩阵重复提交拦截 | PASS |
| 6 | `test_archive_records_raw_and_metadata` | 配置、哈希、原始解、日志、无凭据字段 | PASS |
| 7 | `test_failure_stages_and_resume` | submit/run/download 分类；恢复不重提 | PASS |
| 8 | `test_archive_never_overwritten` | 原始解禁止覆盖 | PASS |
| 9 | `test_attach_platform_report` | 平台报告与设备信息归档 | PASS |

测试使用 3×3/4×4 教学矩阵与 `MockCIMOptimizer`，不访问网络、不调用 license、不消耗配额。

### 3.2 工程自检

命令：`python code/verify_project.py`

```text
[4] 程序入口语法检查   已检查 20 个脚本
[5] 路径可移植性       未发现盘符绝对路径或 sys.path 注入
[7] dry-run 安全性     退出码 0；含 [DRY-RUN]；未触发 license 输入
[8] SHA256 校验        43/43 一致
结论：PASS 15 项 | FAIL 0 项 | BLOCKED 0 项 | WARN 1 项（lightgbm 可选未装）
```

### 3.3 CLI 冒烟（真实输入、仅 dry-run）

登记 `code/predictions/pool_q2_phys.csv`（X=NO2，52×52）后执行 `plan` / `run`：

| 项目 | 输出 |
|---|---|
| QUBO / Ising | 26 比特 → 27 比特（辅助自旋 1 个，末位） |
| 罚项 M | 58.233 |
| 目标分辨率 | 原始 Ising 1.87 档 / 8bit 适配后 2.00 档 |
| 配额 | 优化 32 / 已用 0 / 剩余 32（verified=False） |
| 落盘 | 仅 `inputs/<version>/` 与 `config/quota_budget.json`，无 `tasks/` |

---

## 4. 未解决问题

| # | 问题 | 状态 | 建议 |
|---|---|---|---|
| 1 | 真机端到端提交未实测 | BLOCKED | 需账号持有人在交互终端授权后，人工提交 1 个最小任务验证 |
| 2 | 平台任务 ID / 设备型号 `solve()` 不返回 | UNVERIFIED | 从平台 PDF 用 `attach-report` 归档 |
| 3 | 本地配额账本不等于平台余额 | UNVERIFIED | 提交前仍需登录平台核对 |
| 4 | `get_task_result` / `_query_task_status` / `_ising_to_md5_hash` 为私有接口 | UNVERIFIED | 已做兼容降级；SDK 升级后需复测 |
| 5 | H 方向标注、ΔH 系数（见 1.4 A/B） | 待队员核验 | 按约束未修改；确认后再决定是否修正 |
| 6 | 位置解码在引入松弛变量后会错位 | 风险记录 | 本阶段构造无松弛变量；后续改用变量名解码 |
| 7 | 注册表无并发锁 | 已知限制 | 单机单用户；多人协作需改为文件锁 |
| 8 | 平台结果 dict 结构无真实样本 | UNVERIFIED | 首次真实恢复后把原始 dict 归档并复核字段 |

---

## 5. 人工运行说明

授权（仅首次，交互输入，不落盘）：

```powershell
& "$env:LOCALAPPDATA\kaiwu-verify\Scripts\python.exe" code\d_submit_cim.py --init
```

登记输入版本：

```powershell
# 队员提供的长表（A,B,...,V_hat）
& "$py" code\d_experiment.py inputs register --version team_q2_v1 `
    --matrix path\to\team_matrix.csv --format long --value-col V_hat `
    --kind team_model --sub-q Q2

# 已筛好的方阵（首行 B 标签、首列 A 标签）
& "$py" code\d_experiment.py inputs register --version team_q2_v1 `
    --matrix path\to\matrix.csv --format matrix --kind team_model --sub-q Q2
```

预演与查看：

```powershell
& "$py" code\d_experiment.py inputs list
& "$py" code\d_experiment.py inputs show --version team_q2_v1
& "$py" code\d_experiment.py plan --input-version team_q2_v1 --task-name q2_k13 --topk 13
& "$py" code\d_experiment.py run  --input-version team_q2_v1 --task-name q2_k13 --topk 13
```

实际提交（必须交互终端；按提示输入完整 task_id）：

```powershell
& "$py" code\d_experiment.py run --input-version team_q2_v1 --task-name q2_k13 --topk 13 --submit
```

状态、恢复与报告：

```powershell
& "$py" code\d_experiment.py status
& "$py" code\d_experiment.py status --task-id <task_id>
& "$py" code\d_experiment.py resume --task-id <task_id>
& "$py" code\d_experiment.py attach-report --task-id <task_id> --file <report.pdf> `
    --device SPQC-550 --platform-task-id <platform_id>
& "$py" code\d_experiment.py budget
```

---

## 6. PR #3 合并评估（供人工决定）

| 检查项 | 结论 |
|---|---|
| 合并可行性 | MERGEABLE / CLEAN，main 为祖先，可快进 |
| 变更范围 | 仅工程路径、安全开关、记录与文档；`code` 差异中无模型参数、公式、QUBO 系数、随机种子改动 |
| CI | 无任何检查 |
| 人工评审 | 0 review / 0 comment |
| 行为变化 | `d_run_stats.py` 默认改为 dry-run；输出目录调整 |
| 现有阻塞 | 无技术冲突 |

风险：

1. **无评审、无 CI**：合并前至少由一名队员按 `RELEASE_CHECKLIST.md` 第 2 节逐项确认。
2. **CLI 行为变化**：习惯旧命令的队员会以为任务已提交，实际只是 dry-run；需队内同步。
3. **本阶段新增代码尚未提交**：Phase 10 的 7 个新文件当前是工作区改动，不在 PR #3 的 `ddc9635` 中。直接合并 PR #3 不会包含它们。
4. **实验索引数据准确性**：`EXPERIMENT_INDEX.md` 的任务 ID/设备/时长需与平台记录人工核对。

建议：先合并 PR #3（如队内确认），再单独提交 Phase 10 变更并开新 PR；也可将 Phase 10 追加到同一分支后一并评审。**本次未执行任何合并、提交或推送操作。**

---

## 7. 合规声明

- 未提交任何真机任务，未消耗任何配额。
- 未记录、未打印、未写入任何账号、密码、`sdk_code`、Token 或授权字段；归档写出前统一过滤敏感键。
- 未修改数学模型、算法、参数、随机种子、QUBO 系数与研究结论。
- 发现的数学口径问题只提供证据与复现路径，未擅自修改，交参赛队员独立核验。
- 测试全部使用非赛题教学矩阵与模拟后端。
