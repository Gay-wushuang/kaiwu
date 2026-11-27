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
| M1 | 8bit 量化后最优翻转：Q2 k13 LaHf → Sc-Hf/Sc-Zr；Q3 k12 8 个 V=0 → La-Mg/Ge-Hf/Ge-Ti/Ge-Zr | 已验证；论文“量化后精确复现”不成立 | 队员 |
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
| 配额账本、dry-run、人工逐任务确认 | PASS |
| 原始返回归档、失败分类、恢复 | PASS（mock 验证；真实恢复未验证） |
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
