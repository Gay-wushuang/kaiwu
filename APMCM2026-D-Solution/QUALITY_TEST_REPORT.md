# QUALITY_TEST_REPORT.md — Gate 4 自动化测试与回归验收

- 时间：2026-11-27（Asia/Shanghai）
- 分支：`engineering/final-quality`
- 被测代码：`APMCM2026-D-Solution/`
- 主测试环境：`%LOCALAPPDATA%\kaiwu-verify`（CPython 3.12.6，kaiwu 1.4.4）
- 交叉验证环境：`%LOCALAPPDATA%\kaiwu-original`（CPython 3.12.5，队友 9 项依赖）
- 真机任务：0 次；配额消耗：0；凭据读取/记录：0

状态口径：`PASS` / `FAIL` / `BLOCKED` / `UNVERIFIED`。

---

## 1. 测试命令与实际结果

| # | 命令 | 实测结果 | 判定 |
|---|---|---|---|
| 1 | `python -m compileall -q code tests` | 退出码 0，无语法错误 | PASS |
| 2 | `python -m unittest discover -s tests -v` | 26 个测试全部通过，约 2.6 s | PASS |
| 3 | `python code/verify_project.py`（kaiwu-verify） | PASS 15 / FAIL 0 / BLOCKED 0 / WARN 1（lightgbm 可选未装） | PASS |
| 4 | `python code/verify_project.py`（kaiwu-original） | PASS 15 / FAIL 0 / BLOCKED 0 / WARN 0 | PASS |
| 5 | `python code/d_submit_cim.py`（自检，不提交） | 退出码 0；13×13 原始口径 1.87 档；8×8 2.94 档 | PASS |
| 6 | `python code/d_run_stats.py --task-name final_quality_dry --topk 13 --mode opt --samples 10 --dry-run` | 退出码 0；输出 `[DRY-RUN]`；未进入 license | PASS |
| 7 | Gate 2 向量复算脚本（27 个平台解向量） | 最大 \|ΔH\| = 0.000；合法解数 2/7、1/10、1/10 | PASS |

---

## 2. 自动化测试清单（16 项）

| # | 用例 | 验证内容 | 结果 |
|---|---|---|---|
| 1 | `test_input_version_isolation_and_tamper_detection` | 输入版本隔离、篡改检测 | PASS |
| 2 | `test_mixed_kind_refused` | 原始预测/独立复现不得混用 | PASS |
| 3 | `test_dry_run_no_files_no_network` | 断网下 dry-run 成功、不建归档 | PASS |
| 4 | `test_quota_protection_blocks_before_submit` | 预算为 0 时提交前中止 | PASS |
| 5 | `test_duplicate_submission_blocked` | 同任务名/同矩阵重复提交拦截 | PASS |
| 6 | `test_archive_records_raw_and_metadata` | 配置、哈希、原始解、日志、无凭据字段 | PASS |
| 7 | `test_failure_stages_and_resume` | submit/run/download 分类；恢复不重提 | PASS |
| 8 | `test_archive_never_overwritten` | 原始解禁止覆盖 | PASS |
| 9 | `test_attach_platform_report` | 平台报告与设备信息归档 | PASS |
| 10 | `test_unknown_failure_is_conservative` | 未知异常按已提交计、拦截重复 | PASS（新增） |
| 11 | `test_backend_prepare_failure_is_retryable` | 授权/构造失败可同名重试 | PASS（新增） |
| 12 | `test_invalid_solution_shape_rejected` | 非法解原样归档、不标记完成 | PASS（新增） |
| 13 | `test_run_arg_validation` | topk/samples 非法参数本地拦截 | PASS（新增） |
| 14 | `test_validate_spin_matrix` | ±1、列数、空解校验 | PASS（新增） |
| 15 | `test_backup_if_exists_preserves_old_output` | 覆盖前备份旧输出 | PASS（新增） |
| 16 | `test_dry_run_separates_requested_and_returned_samples` | 请求 sample_number 与实际返回解数分离 | PASS（新增） |

测试使用 3×3/4×4 教学矩阵与 `MockCIMOptimizer`，不访问网络、不调用 license、不消耗配额。

---

## 3. Gate 2 实验记录核对结果

方法：从三份平台 PDF 提取全部 27 个解向量，用仓库现有代码重建同一 Ising 矩阵（含罚项倍数与 topk），按 SDK 约定 `H = -sᵀJs` 复算，并统计“恰好一个 A + 一个 B”的合法解数。

| 任务 | 解向量数 | H 最大偏差 | 合法解数 | INDEX 记录 | 判定 |
|---|---:|---:|---:|---|---|
| apmcm_q2_no2_k13 | 7 | 0.000 | 2 | 2 | PASS |
| apmcm_q2_k13_m3x | 10 | 0.000 | 1 | 1 | PASS |
| apmcm_q2_k8_m1x | 10 | 0.000 | 1 | 1 | PASS |

任务 ID、设备型号、硬件时长与 PDF 的逐项对照见 `CODE_AUDIT.md` 第 5.1 节，全部一致。

论文元数据差异见 `CODE_AUDIT.md` 第 5.4 节，属于论文修订事项，未在工程侧修改。

---

## 4. 安全检查

| 检查项 | 结果 | 判定 |
|---|---|---|
| dry-run 是否联网 | 未调用 license、未创建任务；测试中断言无 socket 连接 | PASS |
| 非交互提交 | `confirm_submit` 在非 TTY 下直接中止 | PASS |
| 凭据 | 归档写出前过滤 `authorization/sdk_code/user_id/token/password`；测试断言配置无这些键 | PASS |
| 历史产物 | 本次未改写 `results/` 下任何历史实验文件；新增备份机制只复制不删除 | PASS |
| 配额 | 全程 0 次提交；本地账本未增加真实消耗 | PASS |

---

## 5. 未验证项（UNVERIFIED）

| 项 | 原因 |
|---|---|
| 真实提交 / 恢复流程 | 按约束未提交真机任务；仅用 mock 验证状态机 |
| 平台 `get_task_result` 返回结构 | 无新的真实任务；历史任务未保存原始 dict |
| 论文元数据修订 | 由参赛队员确认与修改 |
| 英文版论文与提交材料 | 不属于本次工程范围 |

---

## 6. 回归结论

- 26/26 自动化测试通过。
- 两套环境 `verify_project.py` 均为 FAIL 0；kaiwu-verify 新增 1 个 WARN（模型与池预测不同批次，属预期告警）。
- 历史脚本自检与 dry-run 行为未变。
- 新增修复均有对应测试，未发现回归。
- 未修改模型、算法、参数、随机种子或科学结论。

---

## 7. 关键缺陷修复回归（2026-11-27）

### 7.1 命令与结果

| 命令 | 结果 | 判定 |
|---|---|---|
| `python -m compileall -q code tests` | 退出码 0 | PASS |
| `python -m unittest discover -s tests -v` | **26/26 PASS**（约 2.6 s） | PASS |
| `python code/verify_project.py`（kaiwu-verify） | PASS 15 / FAIL 0 / BLOCKED 0 / **WARN 2** | PASS（含预期告警） |
| `python code/verify_project.py`（kaiwu-original） | PASS 15 / FAIL 0 / WARN 1 | PASS（含预期告警） |
| `python code/artifact_consistency.py` | 输出 `MISMATCH`，max\|ΔV\|=4.733 | 预期告警 |

WARN 1：lightgbm 在 kaiwu-verify 中未安装（可选依赖）。
WARN 2：模型与池预测不是同一批次（max\|ΔV\|=4.733，mean\|ΔV\|=0.311，exact=0/2704）。这是新增的告警，不是 FAIL。

### 7.2 新增测试（10 项）

| 用例 | 验证内容 |
|---|---|
| `test_load_pool_refuses_duplicate_ab_without_x` | 重复 (A,B) 不再静默覆盖；显式 X 后成功 |
| `test_q3_long_input_requires_explicit_x` | Q3 长表必须声明 `--x-col/--x` |
| `test_artifact_diff_stats` | 模型/预测差异统计与形状检查 |
| `test_h_direction_and_dual_resolution_recorded` | H 方向字段、原始/适配双口径、排序与图注 |
| `test_no_physical_optimum_claim_in_code` | 代码不再出现“穷举金标准/真值最优” |
| `test_qubo_ising_identity_only_in_aux_plus_gauge` | QUBO=H+bias 仅 aux=+1 |
| `test_onehot_penalty_and_aux_degeneracy` | one-hot 罚项、aux 退化、非法解码 |
| `test_spin_flip_delta_h_is_twice_the_code_formula` | ΔH 精确值与代码值关系 |
| `test_quantization_can_change_legal_argmin` | 8bit 量化可改变合法最优（教学矩阵） |
| `test_full_space_optimum_is_not_legal_optimum_without_penalty` | 合法指派最优 ≠ 全空间最优 |

### 7.3 未验证项

| 项 | 原因 |
|---|---|
| 真实提交/恢复 | 未提交真机任务，未消耗配额 |
| 量化翻转对正式结论的影响 | 属科学研究问题，交队员确认 |
| 论文元数据修订 | 由队员完成，见 `PAPER_CORRECTION_LIST.md` |
| 历史提交矩阵/原始模型哈希 | 当时未记录，见 `results/EXPERIMENT_TRACEABILITY.json` |
