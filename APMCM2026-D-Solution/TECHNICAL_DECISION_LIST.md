# TECHNICAL_DECISION_LIST.md — 关键缺陷修复与最终验收决策清单

- 时间：2026-11-27（Asia/Shanghai）
- 分支：`engineering/critical-fixes`（基于 `engineering/final-quality` @ `1502a56`，cherry-pick 审计文档 `996c147`）
- 状态：工程修复与测试已完成；**未合并 main、未推送、未提交真机任务、未消耗配额**
- 证据：`SCIENTIFIC_AUDIT.md`、`PAPER_CORRECTION_LIST.md`、`OPTIMUM_STABILITY_PLAN.md`、`QUALITY_TEST_REPORT.md`、`docs/audit_evidence/20261127/`

---

## 1. 任务 1：审计证据归档

| 项目 | 结果 |
|---|---|
| 临时脚本 | 10/10 已复制到 `docs/audit_evidence/20261127/scripts/`，含 SHA256 |
| 输入哈希 | 数据 8 份、预测 4 份、模型、3 份平台 PDF、论文/题面 PDF，见 `INPUT_HASHES.json` |
| 环境信息 | kaiwu-verify（3.12.6）与 kaiwu-original（3.12.5）的 Python/包版本，见 `ENVIRONMENT.json` |
| PDF 关键值 | 任务 ID/设备/时间/解数/H 范围/分辨率，见 `logs/pdf_key_values.json` |
| 原始控制台日志 | **MISSING**：未保存为文件；已在 `logs/README.md` 明确记录，不补造 |
| 失败脚本 | `science_margins.py` 原样保留（DataFrame 重复列），成功版本为 `science_margins2.py` |

说明：部分脚本依赖修复前的 `load_pool` 行为，在当前分支重跑 Q3 部分会因重复 (A,B) 保护而中止；这是预期保护。

---

## 2. 任务 2：已修复的普通工程缺陷

| # | 缺陷 | 修改 | 行为影响 | 测试 |
|---|---|---|---|---|
| F1 | Hamiltonian 排序与图注错误 | `d_run_stats.py`：样本按 H 升序；图注“越小越好”；stats 增加 `h_direction` | 仅输出顺序/图注；统计值不变 | `test_h_direction_and_dual_resolution_recorded` |
| F2 | 代理模型最优被称为真实物理最优 | `d_submit_cim.py`、`d_run_stats.py`、`run_all.py`：改为“代理模型矩阵精确最优 / 矩阵内精确最优” | 仅文案 | `test_no_physical_optimum_claim_in_code` |
| F3 | 输入重复记录静默覆盖 | `load_pool` 检测重复 (A,B) 并中止；`build_sub` 同样拒绝重复 | Q3 必须显式 X；Q2 不受影响 | `test_load_pool_refuses_duplicate_ab_without_x` |
| F4 | Q3 输入缺少 X 分组声明 | `experiment_input.register`：Q3 长表必须 `--x-col X --x <X>`；manifest 记录 `x_declared` | 仅影响输入登记；**`run_all.py` 已按 X 过滤，正式 Q3 流程不改** | `test_q3_long_input_requires_explicit_x` |
| F5 | 模型与预测文件批次不一致无告警 | 新增 `code/artifact_consistency.py`；`verify_project.py` 第 [9] 项 WARN | 当前仓库得到 WARN（max\|ΔV\|=4.733），不再是静默 | `test_artifact_diff_stats` + verify_project |
| F6 | 原始/量化矩阵统计口径混用 | `d_submit_cim.py`、`d_run_stats.py`、`run_all.py` 同时输出 `resol_raw` / `resol_adj`，逐项标注 | 旧 `resol` 保留（原始口径），新增字段 | `test_h_direction_and_dual_resolution_recorded` |
| F7 | 实验记录/设备/耗时/日志索引 | 仓库 `EXPERIMENT_INDEX.md` 与 PDF 已一致，无需改历史；新增 `results/EXPERIMENT_TRACEABILITY.json`；论文差异交 `PAPER_CORRECTION_LIST.md` | 不覆盖历史 | 人工核对 + 追溯 JSON |

补充：`d_experiment.py` 在 Phase 10 已同时记录 `resol_raw` / `resol_adj`，本次未重复修改；`engineering/final-quality` 的 P0/P1 修复未重复实施。

---

## 3. 任务 3：通用数学接口验证

新增 `tests/test_math_interfaces.py`，只用教学矩阵与小规模枚举：

| 验证项 | 结果 | 说明 |
|---|---|---|
| QUBO 与 Ising 能量定义 | PASS | `QUBO = H + bias` 仅在 `aux=+1` 规范成立；`aux=-1` 不成立 |
| 辅助自旋规范与解码 | PASS | 合法 one-hot 解对 aux 退化；丢弃 aux 解码安全；非法解返回 None |
| 自旋翻转能量差 | PASS | 代码 `2s(Js)-2Jii` = 精确 `ΔH` 的一半；`4s(Js)-4Jii` = 精确值 |
| 量化前后最优集合变化 | PASS | 教学 3×3 矩阵：原始最优 (2,0) → 适配后 (1,0)，集合不相交 |
| 合法状态最优 vs 全空间最优 | PASS | 无罚项时全空间最优是空集/非法状态；加 one-hot 罚项后合法解才成为全空间最优 |

**重要边界**：以上是通用接口验证，不修改正式赛题公式、算法或参数。正式赛题的量化翻转、池内标签重叠等属于科学研究问题，见第 6 节。

---

## 4. 任务 4：实验版本与可追溯性

新增 `results/EXPERIMENT_TRACEABILITY.json`，逐任务记录：

| 任务 | 任务 ID | 设备 | 硬件时长 | 平台 PDF | 数据 SHA256 | 模型 | 提交矩阵哈希 |
|---|---|---|---|---|---|---|---|
| apmcm_q2_no2_k13 | 4cc56fde… | SPQC-550 | 0.6673 ms | 存在 | 存在 | **原始模型 MISSING** | **当时未记录** |
| apmcm_q2_k13_m3x | fa769c1b… | SPQC-550 | 0.9798 ms | 存在 | 存在 | **原始模型 MISSING** | **当时未记录** |
| apmcm_q2_k8_m1x | 3d77a226… | SPQC-1000 | 0.8221 ms | 存在 | 存在 | **原始模型 MISSING** | **当时未记录** |

- 当前 `models/surrogate_phys.joblib` 是独立复现模型（SHA256 `ba22ec9e…`），不是历史原始模型；`EXPERIMENT_VERSION.json` 已注明。
- 提交矩阵哈希仅在 2026-11-27 由当前池与当前代码**反推**，标记 `RECOMPUTED_NOT_ARCHIVED`，不等于当时提交的哈希。
- 未覆盖任何历史结果；新增 JSON 为只读记录。

可追溯性总体：**PARTIAL**。任务级元数据（ID/设备/时间/报告/解数）完整；原始模型与提交矩阵哈希缺失，不能补造。

---

## 5. 任务 5：回归测试

| 命令 | 结果 |
|---|---|
| `python -m compileall -q code tests` | 退出码 0 |
| `python -m unittest discover -s tests -v` | **26/26 PASS**（约 2.6 s） |
| `python code/verify_project.py`（kaiwu-verify） | PASS 15 / FAIL 0 / BLOCKED 0 / WARN 2 |
| `python code/verify_project.py`（kaiwu-original） | PASS 15 / FAIL 0 / BLOCKED 0 / WARN 1 |
| `python code/artifact_consistency.py` | `MISMATCH`，max\|ΔV\|=4.733（预期告警） |

WARN：lightgbm 可选未装；模型与池预测不同批次。无 FAIL、无 BLOCKED。

---

## 6. 任务 6：需人工决策的事项

### 6.1 尚待人工解决的数学/科学问题

| # | 问题 | 现状 | 需谁决定 |
|---|---|---|---|
| M1 | 8bit 量化后合法指派内的最优翻转：Q2 k13 LaHf → Sc-Hf/Sc-Zr；Q3 k12 8 个 V=0 → La-Mg/Ge-Hf/Ge-Ti/Ge-Zr（非全 Ising 空间基态） | 已验证；论文“量化后精确复现”不成立 | 队员 |
| M2 | 三个真机任务的合法样本均属于量化后 argmin 集合 | 已验证；设备没有“漏掉最优”，而是解了量化矩阵 | 队员 |
| M3 | 池内 80.4% 标签重叠；Top-20 中 13/20、15/20 有标签 | 已验证；“盲发现”表述不成立 | 队员 |
| M4 | 模拟退火 ΔH 为精确值一半 | 已验证；等效温度翻倍，不影响枚举/最终排序 | 队员决定是否修 |
| M5 | 辅助自旋位置解码 vs 论文“按变量名解码” | 当前构造正确；改用约束模型会错位 | 队员 |
| M6 | 论文表 5 原始/适配口径混用、位宽定义不一致 | 已验证 | 队员 |
| M7 | 论文分层误差/稀有集命中数无法由已保存预测复现 | UNVERIFIED | 队员补跑或补归档 |

### 6.2 受影响的历史实验

| 任务 | 返回合法样本 | V | 是否属于量化 argmin 集合 | 结论 |
|---|---|---:|---|---|
| 1 | Sc-Zr | 1.266 | 是 | 设备解的是 8bit 矩阵；未量化最优 LaHf 排名 18 |
| 2 | La-B | 10.146 | 是 | 同上；M=3x 下分辨率 1.00 档，量化偏移更大 |
| 3 | Ca-Ta | 2.850 | 是 | 同上；LaHf 仅是五者并列之一 |

因此，论文对“设备未返回最优/合法率低”的解释需要重写；**不是设备故障，而是提交的矩阵已被量化改变**。是否需要重跑真机由队员决定。

### 6.3 是否需要队员重新执行正式研究

- **论文层面：需要。** 至少 C1/C2/C5/C6 必须改写或补充口径。
- **硬件层面：不强制。** 若团队要主张“找到了未量化 QUBO 的物理最优”，需要提高分辨率（变量拆分、更大 k、降低 M）并重新设计实验；这是新的研究方案，本阶段不设计、不提交。
- **模型层面：不要求重训。** 但若要消除“模型/池批次不一致”，需恢复原始模型或重新冻结一次训练产物。
- **禁止**：自动重跑、自动提交、自动改论文。

### 6.4 必须重新核验的论文数字

按 `PAPER_CORRECTION_LIST.md`：

- C1/C2：量化后最优与设备返回解释。
- C3/C4：三任务硬件时长、设备型号。
- C5/C6：标签重叠、模型产物与表 3 可复现性。
- C7/C8：分辨率口径、QUBO/Ising 位宽。
- C9/C10：排队时间、重试表述。
- C12：分层误差、稀有集命中、BaTiO₂S 排名。
- C13/C15：动态范围数值方向、解码方式。
- C16–C20：12 秒倍数、样本列、M 下界、FO₂ 数值。

### 6.5 正式真机运行是否具备工程条件

| 条件 | 状态 |
|---|---|
| 输入版本登记、SHA256、来源隔离 | PASS |
| 原始与量化矩阵归档 | PASS（`input/ising_matrix_raw.csv` + `input/ising_matrix.csv`） |
| 变量映射记录 | PASS（`input/mapping.json`） |
| 原始返回向量归档 | PASS（`raw/solutions.npz`） |
| 设备与硬件耗时记录 | PASS（`attach-report --device --hardware-ms`，PDF 原样归档） |
| 配额账本、dry-run、人工逐任务确认 | PASS |
| 失败分类、恢复 | PASS（mock 验证；真实恢复未验证） |
| 模型/预测批次告警 | PASS（WARN 可见） |
| 科学实验方案（规模、M、配额分配） | **未批准**，由队员设计、本人确认 |
| 当前配额 | 31 SPQC-550 + 1 SPQC-1000，未消耗 |

结论：**工程入口具备条件，科学方案未就绪**。在 M1/M2/M3 的处理方案确认前，不建议提交新的真机任务。

---

## 7. 本阶段 AI 参与范围

已做：代码审计、工程修复、测试、证据归档、文档更新。
未做：修改代理模型/算法/参数/种子、设计正式优化实验、提交真机任务、消耗配额、覆盖历史结果、合并 main、代写科学结论。

## 8. 停止条件

工程侧已停止扩展。等待本人确认：

1. M1/M2 的论文解释与是否重跑；
2. M3 的标签重叠表述；
3. M4/M5 是否修代码；
4. 是否合并 `engineering/critical-fixes`。

---

## 9. 正式研究版本冻结验收（2026-11-27）

### 9.1 合并前检查

| 项目 | 结果 |
|---|---|
| 当前分支/提交 | `engineering/critical-fixes` @ `267fcfd`（工作区干净） |
| main 是否为祖先 | 是；可 **fast-forward**，无冲突 |
| 自动化测试 | **26/26 PASS**（约 2.8 s） |
| 工程自检 | PASS 15 / FAIL 0 / BLOCKED 0 / WARN 2（lightgbm 可选；模型/池批次不一致） |
| 历史实验产物 | 未修改；相对 main 仅新增 `results/EXPERIMENT_TRACEABILITY.json` 与复现池预测 |
| 合并阻塞 | 无技术阻塞；分支包含 PR #4（`engineering/final-quality`）的全部提交，合并后 PR #4 可关闭 |
| 远端状态 | 分支尚未推送；创建 PR 前需 push |

结论：**可以合并**；是否合并、关闭 PR #4 由本人决定。

### 9.2 两套可选基线

| 项目 | A. 队友原始预测 + 历史实验 | B. 独立复现模型 + 预测 |
|---|---|---|
| 定位 | 论文表 3 / 历史真机的正式产物 | 独立复现，用于核验工程可复现性 |
| 代码 commit | 预测 `779cbae`；实验索引记录 `db624f1` | `822b7ea`（复现记录；代码内容与当前 main 的 `code/` 一致） |
| 数据 | 02 `973e6a6d…`、03 `42a62b0f…`、04 `8ed9d46b…` | 同一套数据，哈希相同 |
| 模型 | **原始模型 MISSING**（仓库 joblib 不是 A） | `models/surrogate_phys.joblib` `ba22ec9e…`（与 3.12.5 复现模型同哈希） |
| Q2 预测 | `code/predictions/pool_q2_phys.csv` `41937214…` | `results/reproduction_20261127/predictions/pool_q2_phys.csv` `e818443c…` |
| Q3 预测 | `code/predictions/pool_q3_phys.csv` `6c4544b5…` | `results/reproduction_20261127/predictions/pool_q3_phys.csv` `37c21d9d…` |
| 盲池预测 | q2b `0fe375b6…`、q3b `ecc09980…` | q2b `5898af30…`、q3b `f362fa5a…` |
| 依赖/环境 | 队友 `requirements.txt`（9 项）、Python 3.12.5/Win11（声明） | kaiwu-original 3.12.5（9 项对齐；freeze 55 项）；3.12.6 结果逐字节一致 |
| 历史实验 | 3 个真机任务、PDF 齐全；任务 1 统计/样本/结果图 MISSING；任务 2/3 结果 CSV MISSING | 无真机；`results/reproduction_20261127/` + `run_20261127/` 复现交付物 |
| 完整性 | 预测/报告完整；模型与提交矩阵哈希缺失 | 模型/预测/结果完整；无真机证据 |
| 结论 | **PARTIAL**：可作为论文历史基线，但模型不可复现 | **完整（工程复现）**：可作独立核验基线，不代表历史真机 |

**禁止混用**：仓库当前 `models/` 是 B，`code/predictions/` 是 A。`verify_project` 第 [9] 项已对此告警（max|ΔV|=4.733）。选择 A 时不要引用当前 joblib；选择 B 时不要引用 `code/predictions/` 的原始池。

### 9.3 本人必须作出的技术决策

1. **最终采用 A 还是 B**（或分用途：论文历史结果用 A、工程复现用 B）；不得把两者指标混在同一张表。
2. **8bit 量化解释**：论文改为“设备求解量化矩阵”，还是提高分辨率/变量拆分后重跑；后者需新的实验方案与授权。
3. **是否修 ΔH 系数/温度**：影响 SA 轨迹，不影响精确枚举与最终排序。
4. **论文修订范围**：C1/C2/C3/C4/C5/C6/C7/C8 等，见 `PAPER_CORRECTION_LIST.md`。
5. **是否合并 `engineering/critical-fixes`**、是否关闭 PR #4。

### 9.4 正式实验前仍存在的阻塞项

| 阻塞项 | 类型 | 说明 |
|---|---|---|
| 原始模型产物缺失 | 科学/复现 | 历史任务无法用当前 joblib 精确复现 |
| 历史提交矩阵哈希缺失 | 科学/复现 | 只能反推，不能替代当时记录 |
| 量化改变合法最优集合 | 科学 | 需队员决定论文解释或重跑 |
| Q3 无真机验证 | 科学 | 三次任务均为 Q2；Q3 只有本地枚举 |
| 论文逐行预测证据缺失 | 论文 | 分层误差/稀有集数字无法由已保存文件复现 |
| 新真机实验方案未批准 | 流程 | 任何提交需本人书面授权；当前 31+1 配额未动 |

### 9.5 AI 参与范围（本阶段）

已做：合并前检查、基线整理、归档字段补全、离线测试、文档记录。
未做：选择竞赛基线、修改模型/算法/论文结论、设计正式优化实验、提交真机任务、消耗配额、合并 main。

---

## 10. 最终工程交接（2026-11-27）

### 10.1 最终版本

| 项目 | 值 |
|---|---|
| 分支 | `main` |
| 代码提交（合并后） | `300d2e4`（`engineering/critical-fixes` 快进合并；main 相对 origin 领先 6 个提交） |
| 交接记录 | 本文件本次更新；`git log -1` 为最终交接提交 |
| 合并方式 | fast-forward，无冲突；包含 PR #4（`engineering/final-quality`）全部提交 |
| 远端 | 合并后推送 `main`；`engineering/critical-fixes` 分支保留 |
| 真机/配额 | 0 次提交、0 配额消耗；31 SPQC-550 + 1 SPQC-1000 未动（以平台为准） |

### 10.2 基线采用

- **正式后续研究版本：B（独立复现模型 + 预测）**。
- **历史实验对照：A（队友原始预测 + 三次真机结果）**。
- 两套产物**不得混用**：`models/` 是 B，`code/predictions/` 是 A；`verify_project` 第 [9] 项持续告警（max\|ΔV\|=4.733）。

基线 B 一致性复核（2026-11-27）：

| 检查 | 结果 |
|---|---|
| 模型 SHA256 | `ba22ec9e…`，与 3.12.5 复现模型一致 |
| 四个池预测 vs 模型推理 | **全部 OK**；max\|ΔV\| 分别为 6.7e-6 / 6.7e-6 / 4.8e-6 / 5.1e-6（容差 1e-4） |
| 三个交付 CSV | 与 `reproduction/original_env_20261127/run_20261127/` 逐字节一致（9395cb54 / 7cf63c8c / c53d6337） |
| 依赖 | kaiwu-original 3.12.5，9 项直接依赖，`pip check` 无冲突 |
| 说明 | 同批次约 1e-6 的差来自 float32/CSV 往返，不是批次差异 |

### 10.3 原始浮点 Ising 矩阵无损归档

- 新增 `input/ising_matrix_raw.npz`（`np.savez`，float64 原样保存）。
- 写入后立即回读，`numeric_matrix_sha256` 与写入前一致才继续；`hashes.json` 同时记录：
  - `raw_ising_matrix_sha256`
  - `raw_ising_matrix_npz_sha256`
  - `raw_ising_matrix_readback_sha256`
- 测试：`test_archive_records_raw_and_metadata` 断言 npz 存在、回读哈希相等、shape 与 config 一致。
- CSV 仍保留（`%.10g`，供人工查看），但**以 npz 为无损权威副本**。

### 10.4 研究入口（供本人独立核验）

| 目的 | 入口 |
|---|---|
| 数学接口（QUBO/Ising、aux、ΔH、量化、合法 vs 全空间） | `tests/test_math_interfaces.py`；`python -m unittest discover -s tests -p test_math_interfaces.py -v` |
| 模拟退火 ΔH 源码 | `code/local_sa_stats.py`（`dH = 2 * ...`）、`code/run_all.py` 的 `solve_block` |
| 8bit 量化与分辨率 | `code/d_submit_cim.py` 的 `resolution_pair` / `analyse`；`code/d_run_stats.py`；`code/d_experiment.py` 的 `build_problem` |
| 科学审计证据 | `SCIENTIFIC_AUDIT.md` 第 1.2/1.4 节；`docs/audit_evidence/20261127/`（脚本、哈希、PDF 摘录） |
| 论文修订清单 | `PAPER_CORRECTION_LIST.md` |
| 批次一致性告警 | `python code/artifact_consistency.py`；`verify_project.py` 第 [9] 项 |
| 正式实验入口 | `python code/d_experiment.py inputs register / plan / run`（默认 dry-run；`--submit` 需交互确认） |

端到端教学验证（mock 后端，临时目录）：输入登记 → 建模 → mock 求解 → 归档，以下文件全部存在且哈希回读一致：
`input/matrix.csv`、`mapping.json`、`ising_matrix.csv`、`ising_matrix_raw.csv`、`ising_matrix_raw.npz`、`hashes.json`、`raw/solutions.npz`、`raw/solution_energy.csv`、`config.json`、`task.json`。
设备与硬件耗时可通过 `attach-report --device --hardware-ms` 录入。

### 10.5 最终验收

| 项目 | main @ `300d2e4` |
|---|---|
| 26 项测试 | PASS（2.874 s） |
| compileall | PASS |
| verify_project | PASS 15 / FAIL 0 / BLOCKED 0 / WARN 2 |
| 历史结果 | 未修改；仅新增追溯 JSON 与基线 B 预测 |
| 工作区 | 干净 |

### 10.6 剩余阻塞项（均需人工决策）

1. 原始模型产物缺失；历史任务无法用当前 joblib 精确复现。
2. 历史提交矩阵哈希缺失；只能反推。
3. 8bit 量化改变合法指派内的最优集合；论文解释或重跑方案未定。
4. Q3 尚无真机验证（三次任务均为 Q2）。
5. 论文部分指标缺少逐行预测证据（分层误差、稀有集命中）。
6. 新真机实验方案未批准；任何提交需本人书面授权。

### 10.7 AI 参与范围声明

本阶段 AI 仅执行：合并前检查、快进合并、基线 B 一致性验证、无损归档字段补全、离线教学测试、交接记录。
未执行：核心数学修改、优化方案设计、正式求解实验、真机提交、配额消耗、论文结论改写。
