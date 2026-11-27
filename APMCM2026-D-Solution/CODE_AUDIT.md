# CODE_AUDIT.md — Gate 1 / Gate 2 代码与实验记录审计

- 审计时间：2026-11-27（Asia/Shanghai）
- 分支：`engineering/final-quality`（基于 `main` @ `a372327`）
- 审计对象：`APMCM2026-D-Solution/`
- 证据优先级：平台原始 PDF > 原始日志/逐样本文件 > `EXPERIMENT_INDEX.md` > README > 论文
- 边界：未修改数学模型、算法、参数、随机种子与科学结论；未提交真机任务；未消耗配额

状态口径：`PASS` / `FAIL` / `BLOCKED` / `UNVERIFIED`。

---

## 1. 审计结论摘要

| 级别 | 数量 | 处理 |
|---|---:|---|
| P0 | 1 | 已修复并测试 |
| P1（工程） | 5 | 已修复 5 项 |
| P1（数学/术语，需队员确认） | 4 | 仅记录，未修改 |
| P2 | 9 | 记录，不追求全部关闭 |
| Gate 2 实验记录 | — | 任务级全部一致；论文元数据 4 处不一致 |

没有未处理的 P0；涉及数学与科学表述的问题已全部移交参赛队员。

---

## 2. P0 / P1 工程缺陷与处理

### E1（P0）未知阶段失败被当成“未提交”，导致配额少计与重复提交风险

- 位置：`code/d_experiment.py:361-363`
- 原行为：`classify_error` 返回 `unknown` 时，状态映射默认落到 `submit_failed`，`counted=False`。
- 风险：如果云端任务实际已创建，但异常文本未匹配已知模式（例如下载解析阶段的其他异常），账本会少计 1 次配额，且同名/同矩阵的重复提交不会被拦截。
- 修复：`unknown` 映射为 `unknown_failure`，`quota_counted=True`；`find_duplicate` 不会跳过该状态。
- 测试：`test_unknown_failure_is_conservative`。

### E2（P1）授权或优化器构造失败留下 “created” 状态，阻塞重试

- 位置：`code/d_experiment.py:322`（原 292-294 行在 try 之外）
- 原行为：`kw.license.verify_license` 或 `CIMOptimizer(...)` 抛错时，任务已登记为 `created`，但没有失败记录；重复提交检查只跳过 `submit_failed` / `cancelled`，导致同名重试被自己阻塞。
- 修复：后端准备封装为 `_prepare_backend`，异常统一记为 `submit_failed`、`quota_counted=False`、`error_stage=prepare:*`。
- 测试：`test_backend_prepare_failure_is_retryable`（失败后同名 mock 重试成功）。

### E3（P1）真机返回解缺少格式校验

- 位置：
  - `code/experiment_archive.py:109`（新增 `validate_spin_matrix`）
  - `code/d_experiment.py:379`、`:467`
  - `code/d_submit_cim.py:164`
  - `code/d_run_stats.py:70`
- 原行为：直接把返回数组按 `[:nA+nB]` 截断解码，未检查列数是否等于 Ising 比特数、取值是否只有 ±1。
- 风险：SDK 版本变化或异常返回会被静默解码成错误候选，结果文件看起来“正常”。
- 修复：校验二维、列数、±1 取值；`d_experiment` 失败时原样归档并标记 `invalid_result`（计配额、拦截重复提交），历史脚本直接中止且不写结果文件。
- 测试：`test_invalid_solution_shape_rejected`、`test_validate_spin_matrix`。

### E4（P1）历史脚本重跑会静默覆盖旧结果

- 位置：`code/experiment_archive.py:127`（新增 `backup_if_exists`）；`code/d_submit_cim.py:179`；`code/d_run_stats.py:110`
- 原行为：`results/<task>_result.csv`、`cim_stats/*.json`、`cim_samples/*.csv`、`*_H_hist.png` 重名时直接覆盖。
- 修复：写入前把已有文件复制为 `*.bak-YYYYMMDD-HHMMSS`，原文件保留，不改变主输出路径与内容。
- 测试：`test_backup_if_exists_preserves_old_output`。

### E5（P1）`d_run_stats` 未记录“请求的 sample_number”与“实际返回解数”的区别

- 位置：`code/d_run_stats.py:51`、`:95`
- 原行为：统计 JSON 的 `samples` 是实际返回解数，但没有记录命令行请求值。优化模式下 `--samples 200` 与实际返回 10 个解容易混淆（历史 `run_m3x.log` 即为此情形）。
- 修复：dry-run 返回 `sample_number_param`、`returned_solutions=None`；提交统计新增 `sample_number_param`，`returned_solutions` 记录实际数，`samples` 保持“实际返回”语义。
- 测试：`test_dry_run_separates_requested_and_returned_samples`。

### E6（P1）README 脚本数量与实际不一致

- 位置：`README.md:10`
- 原行为：写“15 个 .py”，实际 `code/*.py` 为 20 个。
- 修复：更新为 20，并补充 Phase 10 基础设施说明。
- 验证：`Get-ChildItem code -Filter *.py` 计数 20。

---

## 3. P1 数学 / 统计 / 术语问题（仅记录，交队员确认）

> 以下问题可能影响论文表述或实验解释，不属于普通工程缺陷。**本次未修改。**

### A1（P1）Hamiltonian 方向：图注与排序写反

- 位置：`code/d_run_stats.py:113`（按 `H` 降序写样本 CSV）、`:121`（图注“越大越好”）。
- SDK 定义：`kw.common.hamiltonian` 返回 `-sᵀJs`；本地 3 变量样例验证 `QUBO 值 = H + bias`，因此 **H 越小越好**。
- 平台证据：用仓库代码重建矩阵后，三份 PDF 的 27 个解向量 H 全部逐值复算一致（最大 |ΔH| = 0.000）；合法解都是 H 最小的那一个/两个：

| 任务 | 合法解 H | 其余解 H 范围 |
|---|---:|---|
| apmcm_q2_no2_k13 | −3008 / −2972 | −2964 … 5508 |
| apmcm_q2_k13_m3x | −3126 | −3086 … 8930 |
| apmcm_q2_k8_m1x | −1796 | −1732 … 3228 |

- 影响：`valid_rate`、`best_V` 等统计按全体样本独立计算，未被排序影响；但样本 CSV 顺序与图注会误导读者。
- 待确认：是否把排序改为升序、图注改为“越小越好”，或明确写成“能量，取最小”。

### A2（P1）模拟退火 ΔH 系数为精确值的一半

- 位置：`code/local_sa_stats.py:36`、`code/run_all.py:186`
- 推导：`H = -sᵀJs`、J 对称；翻转自旋 i 的精确能量差为 `ΔH = 4·s_i·(Js)_i − 4·J_ii`。代码写的是 `2·s_i·(Js)_i − 2·J_ii`，即 `ΔH/2`。
- 影响：Metropolis 接受概率实际为 `exp(−ΔH/(2T))`，等效温度翻倍。精确枚举、目标函数和最终最优值不受影响；退火轨迹与“温度”解释不一致。
- 待确认：是否修正为 `4·…`，或把温度参数减半，并在论文中说明。

### A3（P1）辅助自旋按位置截断，而不是按变量名解码

- 位置：`code/d_submit_cim.py:172`、`code/d_run_stats.py:79`
- 现状：QUBO n 比特 → Ising n+1 比特，辅助自旋固定在末位（SDK 源码与 3×3 实测确认），因此 `[:nA+nB]` 当前正确。
- 风险：预研仓库 `AGENTS.md` 的约定是“按变量名读取，不按数组位置（约束会自动插入松弛变量）”。若后续改用带约束的 `QuboModel`，位置截断会静默错位。
- 附带：`d_run_stats.py:56` 用 `adj.shape[0] - 1` 当 QUBO 比特数，只有“恰好 1 个辅助自旋”时成立，属脆弱写法。

### A4（P1）分辨率存在两套口径

- 原始 Ising 矩阵口径：13×13 为 1.87 档；8bit 精度适配后矩阵口径：2.00 档（8×8 为 3.00 档）。
- 位置：`code/d_submit_cim.py:59-65` 与 `code/d_run_stats.py:31-43`；`docs/ENGINEERING_ACCEPTANCE.md` 与论文混用。
- 现状：`d_experiment plan` 同时打印两种口径；本次不改公式。
- 待确认：论文正文统一注明口径，或只保留一种。

### A5（P1）“穷举金标准”指代理模型矩阵的最优，不是真实物理最优

- 位置：`code/d_submit_cim.py:94`、`:176`；`code/run_all.py` 中“精确最优”。
- 现状：`gold` 来自 `V`（即 `V_hat` 矩阵）的 `argmin`，是“代理模型预测下的精确最优”，不等于真实 DFT 标签的最优。
- 风险：若论文/答辩把“命中金标准”理解为“命中真实材料”，属于术语夸大。
- 待确认：统一改为“代理模型矩阵精确最优”或“池内精确最优”。

### A6（P1）优化模式返回解数与独立采样次数混用

- 位置：`code/d_submit_cim.py:152-154` 的确认文案把 `sample_number` 显示为“采样数量”，即使模式为 optimization。
- 事实：`run_m3x.log` 显示“模式 opt 采样 200”，平台实际返回 10 个解；`d_run_stats` 现已分开记录请求值与实际返回数。
- 待确认：确认文案与论文表述是否区分“SDK 参数”与“平台实际返回解数”。

---

## 4. P2 记录（本次不修）

| ID | 位置 | 问题 |
|---|---|---|
| P2-1 | `code/run_all.py:108` | `if False else` 死代码；功能正确但可读性差 |
| P2-2 | `code/d_run_stats.py:89` | `top8` 变量未使用 |
| P2-3 | `code/d_step12.py`、`d_baseline.py`、`d_route_compare.py`、`d_step3.py` | 探索脚本写入 `code/predictions/` 或 `results/`，与主线共用命名空间，存在版本混用风险 |
| P2-4 | `code/experiment_archive.py` Registry | 单机单用户，无文件锁；多人并发需加锁 |
| P2-5 | `code/d_experiment.py` `inputs register --format auto` | CSV 默认按长表解析；方阵需显式 `--format matrix` |
| P2-6 | `code/experiment_archive.py:174` | mock 任务也计入本地配额账本；生产使用前需注意 |
| P2-7 | `code/verify_project.py` | `EXPECTED_OUTPUTS` 依赖 `train_q1.py`/`model_compare.py` 等脚本产物，单独跑 `run_all.py` 不足以全部生成 |
| P2-8 | `code/d_submit_cim.py:152` | 优化模式确认文案仍写“采样数量” |
| P2-9 | `docs/ENGINEERING_ACCEPTANCE.md` | 仍写“15 个脚本”，与实际 20 个不一致 |

---

## 5. Gate 2：实验记录一致性

### 5.1 平台 PDF 与索引逐项核对

以 `results/vendor_reports/*.pdf` 原文为最高优先级；并用仓库代码重建同一矩阵，机械复算 PDF 解向量的 Hamiltonian 与合法解数（只做结构校验，不解释科学含义）。

| 项目 | apmcm_q2_no2_k13 | apmcm_q2_k13_m3x | apmcm_q2_k8_m1x |
|---|---|---|---|
| PDF 任务 ID | `4cc56fde…feef` | `fa769c1b…4d5a` | `3d77a226…b416` |
| INDEX 任务 ID | 一致 | 一致 | 一致 |
| PDF 设备 | SPQC-550 | SPQC-550 | SPQC-1000 |
| INDEX 设备 | 一致 | 一致 | 一致 |
| PDF 硬件时长 | 0.6673 ms | 0.9798 ms | 0.8221 ms |
| INDEX 硬件时长 | 一致 | 一致 | 一致 |
| PDF 返回解数 | 7 | 10 | 10 |
| INDEX 返回解数 / 合法数 | 7 / 2 | 10 / 1 | 10 / 1 |
| 机械复算合法数 | 2 | 1 | 1 |
| 机械复算 H 最大偏差 | 0.000 | 0.000 | 0.000 |

结论：**任务级记录与平台 PDF 完全一致**，包括此前容易被误写的设备型号、硬件时长、返回解数与合法解数。

### 5.2 文件完整性

| 任务 | 平台 PDF | 统计 JSON | 逐样本 CSV | 结果 CSV | H 图 |
|---|---|---|---|---|---|
| no2_k13 | 存在 | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| k13_m3x | 存在 | 存在 | 存在 | **MISSING** | 存在 |
| k8_m1x | 存在 | 存在 | 存在 | **MISSING** | 存在 |

`EXPERIMENT_INDEX.md` 已逐项标记 MISSING；本次未补造任何文件。

### 5.3 下载重试的表述

- `results/logs/run_m3x.log`：任务完成后下载 SSL 中断。
- `results/logs/run_m3x_retry.log`：仅出现 `Task completed` 与“返回 10 个解”，**没有** `Task submit` 行。
- 事实：重试复用了服务端同名同矩阵结果，未重新提交、未再消耗配额。
- 论文 p21 写“下载失败后没有重试”，与日志不符；建议改为“未重新提交任务，仅重新下载已有结果”。

### 5.4 论文与原始记录的元数据差异（交队员）

| # | 论文位置 | 论文写法 | 原始记录 |
|---|---|---|---|
| 1 | 表 15 | 三行硬件时长均为 0.6673 ms | 0.6673 / 0.9798 / 0.8221 ms |
| 2 | 第 1 页 | 三组实验均在 SPQC-550 | 任务 3 为 SPQC-1000 |
| 3 | 第 21 页 | 下载失败后没有重试 | `run_m3x_retry.log` 复用结果，未重新提交 |
| 4 | 第 15 页 | 排队时间每次 12–13 秒 | 任务 2/3 创建到结束各约 4 秒（14:40:12→16、14:47:39→43） |
| 5 | 第 1 页 | 分辨率 2.00 档 | 第 11/12 页为 1.87 档（原始 Ising 口径） |

以上只报告差异与证据位置，未修改论文内容或研究结论。

### 5.5 历史任务的可追溯性缺口

- 三次历史任务没有保存“输入文件 SHA256 / 实际提交矩阵 SHA256 / SDK 版本”的任务级记录；`EXPERIMENT_INDEX.md` 仅记录代码版本 `db624f1`。
- 本次已用仓库代码重建矩阵并逐值复算 H，证明当前代码与历史提交矩阵一致；但这是事后验证，不等同于当时的输入哈希。
- 不补造历史哈希；后续任务由 `d_experiment.py` 自动记录。

---

## 6. 待参赛队员确认的事项

| # | 事项 | 状态 |
|---|---|---|
| 1 | A1：Hamiltonian 排序方向与图注 | 待确认 |
| 2 | A2：退火 ΔH 系数与温度定义 | 待确认 |
| 3 | A3：是否改为按变量名解码 | 待确认 |
| 4 | A4：论文统一分辨率口径 | 待确认 |
| 5 | A5：“金标准”术语改为“代理模型矩阵精确最优” | 待确认 |
| 6 | A6：优化模式确认文案与论文表述 | 待确认 |
| 7 | 5.4 节论文元数据 4 处不一致 | 待确认 |
| 8 | 任何新的真机提交（任务数、规模、配额） | 待书面授权 |

---

## 7. 收工条件对照

| 条件 | 状态 |
|---|---|
| 无未处理 P0 | PASS（E1 已修复） |
| 必要 P1 已关闭 | PASS（E2–E6） |
| 数学/科学正确性问题已移交 | PASS（A1–A6 已记录） |
| 自动化测试通过 | PASS（16/16） |
| 历史实验产物未被覆盖 | PASS（本次仅新增备份机制与文档） |
| 真机入口离线安全验收 | PASS（dry-run / 非交互拦截 / 配额保护） |
| 结果可追溯至代码与输入版本 | 历史任务 PARTIAL；后续任务 PASS |
| 源码与支撑材料具备交付条件 | 除论文元数据与英文版外，工程侧 PASS |
