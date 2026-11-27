# RELEASE CHECKLIST — Phase 9 版本冻结与最终工程交付

- 冻结时间：2026-11-27（Asia/Shanghai）
- 工程分支：`engineering/reproducibility`（已并入 `main`）；最终质量冲刺在 `engineering/final-quality`（未合并、未推送）
- 冻结代码：`822b7ea`（Phase 9 仅新增文档、依赖锁与归档，不改代码逻辑）
- PR：#3 <https://github.com/Gay-wushuang/kaiwu/pull/3>，已于 2026-11-27 合并（merge commit `eded807`）；Phase 10 补充修复 `101ff28`
- 边界：未修改模型、算法、参数、随机种子与科学结论；未提交真机任务；未消耗配额

状态口径：`PASS` / `FAIL` / `BLOCKED` / `UNVERIFIED`。

---

## 1. 版本冻结

| 项目 | 状态 | 证据 / 说明 |
|---|---|---|
| 代码冻结 | PASS | 冻结代码 `822b7ea`；PR #3 已于 2026-11-27 合并（`eded807`），合并后补充 `28df547` / `101ff28` |
| 官方原始数据 | PASS | `date/` 8 个 CSV，SHA256 与官方 `sha256_public.json` 全部一致；行数/列数匹配 |
| 本机完整依赖锁定 | PASS | `requirements.lock.txt`（CPython 3.12.6，54 个包） |
| 原始实验环境依赖清单 | PASS（直接依赖）/ PARTIAL（传递依赖） | 队友已提供 `requirements.txt`（9 项）与 `REPRO_NOTES.md`，归档于 `docs/reproduction/original_environment/` |
| 双环境逐包差异 | PASS（直接依赖 9/9）/ PARTIAL（传递依赖） | 直接依赖逐项对照见 `docs/reproduction/original_environment/ENVIRONMENT_REPORT.md`；队友未提供传递依赖 |
| 原始 / 独立复现归档隔离 | PASS | 原始在 `results/`；复现在 `results/reproduction_20261127/`，互不覆盖 |
| 结果替换 | PASS | 未用复现结果替换原始结果；差异单独记录 |
| 数值差异归因 | PASS（审慎） | 已记录依赖差异，但**未认定其为唯一原因** |

双环境已知差异（仅记录，不作结论）：

| 依赖 | 独立复现环境 | 原始环境 |
|---|---|---|
| Python | 3.12.6 | 3.12.5（队友材料） |
| kaiwu | 1.4.4 | 1.4.4 |
| numpy | 2.5.5 | 2.4.4 |
| scikit-learn | 1.9.1 | 1.8.0 |
| scipy | 1.18.1 | 1.17.1 |
| xgboost | 3.4.1 | 3.4.1 |
| lightgbm | 未安装 | 4.7.0 |
| mendeleev | 1.4.0 | 1.4.0 |
| matplotlib | 3.10.3 | 3.10.3 |
| 操作系统 | Windows 10 19045 | Windows 11 |

### 1.1 Phase 10 补充：原始环境对齐（2026-11-27）

| 项目 | 结果 |
|---|---|
| 原始材料归档 | PASS：`REPRO_NOTES.md` / `requirements.txt` / `same_protocol_metrics.json`，含 SHA256 |
| 直接依赖版本未知 | **已解除**：9/9 项按队友 `requirements.txt` 安装 |
| 独立对齐环境 | `%LOCALAPPDATA%\kaiwu-original`，CPython 3.12.5 |
| 依赖安装 | PASS：`pip check` 无冲突；10 个模块导入全部 OK |
| 正式复跑 | PASS：2026-11-27，20.8 s；指标与 3.12.6 独立复现完全一致，三个交付文件逐字节一致（`reproduction/original_env_20261127/run_20261127/COMPARISON.md`） |
| 全量锁定 | `docs/reproduction/original_environment/requirements.freeze.txt`（55 项） |
| 与 kaiwu-verify 差异 | lightgbm 新增；numpy / scikit-learn / scipy 三个版本不同；其余 51 项一致 |
| kaiwu-verify 保护 | PASS：`pip freeze` 与 `requirements.lock.txt` 逐包一致，未降级、未覆盖 |
| 操作系统 | **不一致**：队友 Windows 11，本机 Windows 10 19045；不得宣称环境完全相同 |
| 传递依赖 | PARTIAL：队友未提供，无法逐包核对 |
| 复现入口 | `reproduction/original_env_20261127/run_reproduction.ps1`（临时目录运行，不覆盖历史产物） |
| 三种口径 | `docs/reproduction/PROTOCOLS.md`（02→03 / 分组 OOF / 04 官方盲测） |

---

## 2. PR #3 最终工程验收

| 检查项 | 状态 | 证据 |
|---|---|---|
| 路径修复保持程序逻辑 | PASS | `git diff main...HEAD -- code` 中无模型参数、公式、QUBO 系数、随机种子改动行 |
| dry-run 不创建云端任务 | PASS | `d_run_stats.py --dry-run` 在 license 校验前返回，输出 `[DRY-RUN]` |
| 非交互终端无法提交 | PASS | 关闭 stdin 执行 `--submit`，在二次确认处中止，未进入 license |
| 账号凭据保护 | PASS | 已移除 `--user-id/--sdk-code`；授权仅 `--init` 交互输入；工作区与历史无凭据字面量 |
| 官方数据排除版本管理 | PASS | `date/` 在 `.gitignore`；`git ls-files` 无数据文件 |
| 模型产物排除版本管理 | PASS | `models/` 在 `.gitignore`；模型仅本机存在（SHA 见版本清单） |
| README 与实际程序一致 | PASS | 15 个脚本、命令、`--submit` 语义、论文目录说明均已对齐 |

待队友审查事项（不阻塞工程验收，但影响合并决策）：

1. `d_run_stats.py` 默认行为由“直接提交”改为“dry-run”，提交需显式 `--submit`。
2. 预测与统计输出目录调整为 `code/predictions/`、`results/cim_stats/`、`results/cim_samples/`。
3. `results/EXPERIMENT_INDEX.md` 中的任务信息是否与平台记录一致。

PR 合并状态：**已合并**（2026-11-27，merge commit `eded807`）；合并后修复换行哈希问题 `101ff28`。

---

## 3. 实验版本管理

清单文件：`results/EXPERIMENT_VERSION.json`。

| 项目 | 状态 | 说明 |
|---|---|---|
| Git commit SHA | PASS | 原始 `db624f1`；复现 `822b7ea` |
| 官方数据 SHA256 | PASS | 8 个 CSV 全部记录 |
| Python / 依赖版本 | PASS | 复现环境完整记录；原始环境直接依赖 9/9 已由队友提供并安装验证（传递依赖 PARTIAL） |
| 实验运行时间 | PASS | 原始 29.1 s；复现 74.0 s |
| 随机种子 | PASS（源码级） | `random_state=0`、`np.random.default_rng(7)`，位置见清单 |
| 预测文件 SHA256 | PASS | 四个池的预测与提交文件哈希已记录 |
| 模型产物 SHA256 | PASS（复现） | `models/surrogate_phys.joblib`，15,509,867 B；原始模型未归档 → UNVERIFIED |
| 真机任务 ID | PASS | 3 个任务 ID 与 PDF/统计文件关联 |
| 原始平台报告路径 | PASS | `results/vendor_reports/*.pdf` |

原始实验结果（冻结）：`results/`，哈希见 `results/ARTIFACT_SHA256.json`。
独立复现结果（单独归档）：`results/reproduction_20261127/`。

---

## 4. 真机运行准备

| 项目 | 状态 | 说明 |
|---|---|---|
| 本机 SDK License | PASS | 已通过 `--init` 交互生成；`verify_license(27)` 通过。仅证明 27 比特权限，不代表配额余额或机型 |
| 凭据输入方式 | PASS | 仅 `d_submit_cim.py --init` 交互 `input`/`getpass`，不落盘、不进命令行历史 |
| 用户确认的设备类型 | UNVERIFIED | 用户答复“尚未登录确认” |
| 用户确认的配额 | UNVERIFIED | 用户答复“3 次及以上”，但未经平台核对 |
| 通用提交接口 | PASS | 参数、矩阵规模、模式、预计消耗均在提交前展示 |
| dry-run 安全性 | PASS | 不调用 license、不创建任务、不消耗配额 |
| 本阶段真机提交次数 | PASS | 0 次；配额消耗 0 |
| 正式实验方案与参数 | 由参赛队员独立决定 | AI 未设计、未选择、未提交 |

如需真机运行，必须先由账号持有人在本机执行授权，并由队员书面确认任务数、矩阵规模与预计消耗。

---

## 5. 提交材料工程检查

| 检查项 | 状态 | 证据 / 位置 |
|---|---|---|
| 英文版论文 | **FAIL** | 仓库与历史中均无英文版；`paper/` 仅中文版与草稿版 |
| 英文正文 | **FAIL** | `APMCM_D_paper_CN.pdf` 含 10,564 个中文字符 |
| 英文图表 | **FAIL** | DOCX 内嵌 `image2.png`（51,360 B = `f_gap_zh.png`）等中文图；仓库已有 `f_*_en.png` 英文版可替换 |
| 英文页眉 | **FAIL** | 页眉为 `TeamDapmcm26306844 第1 页/ 共22 页` |
| 首页摘要 / 第二页目录 | PASS（结构） | 首页摘要、第二页目录；但语言为中文 |
| 页数 | PASS | 22 页，正文 ≤ 25 页 |
| 字号 11/12 | UNVERIFIED | 需人工在 Word/PDF 中核对 |
| 文件名 `#***.pdf` | **FAIL** | 现有 `APMCM_D_paper_CN.pdf`；应为 `Dapmcm26306844.pdf` |
| 承诺书 `#***cns.pdf/.jpg` | **FAIL** | 仓库无承诺书文件 |
| 支撑材料 `#***fj.zip/.rar` | **FAIL** | 仓库无打包文件 |
| 附录源码完整性 | **FAIL** | 附录仅 2 段核心代码，其余指向尚不存在的支撑材料 |
| AI 使用记录 | **FAIL** | 有 `docs/AI_USAGE_LOG.md` 与预研日志，但无提交用统一披露文件 |
| 论文数字与原始报告一致性 | **FAIL** | 见下方 5.1 |
| 提交文件敏感信息 | PASS | PDF/DOCX 中未检出 `sdk_code`/`user_id`/`password`/`token` |

### 5.1 论文数字不一致证据

| 项目 | 论文 | 原始记录 |
|---|---|---|
| gap 两阶段（HistGB） | p1、p6、p7 与 `f_gap_zh.png`：0.324 → 0.513 | `results/metrics.csv`：0.3407 → 0.4808；`train_log.txt`：0.341 → 0.481 |
| 三个任务硬件时长 | p21 表 15：三行均为 0.6673 ms | 三份 PDF：0.6673 / 0.9798 / 0.8221 ms |
| 排队时间 | p15：每次 12–13 秒 | 任务 1 约 12 s；任务 2、3 各约 4 s |
| 设备型号 | p1：三组均在 SPQC-550 | 任务 3 PDF：SPQC-1000 |
| 重试表述 | p21：下载失败后没有重试 | 存在 `run_m3x_retry.log`（复用同名同矩阵任务，未重新提交） |
| 13×13 分辨率 | p1、p15：2.00 档 | `cim_run_k13.log`：1.87 档（两套计算口径） |

以上只报告差异与证据位置，未修改论文内容或结论。

---

## 6. 必须由参赛队员处理的事项

1. **提供原始实验环境依赖清单**（`pip freeze` 或等价记录），解锁双环境逐包对比。—— 直接依赖已提供（9 项，见 `docs/reproduction/original_environment/`）；传递依赖仍待提供。
2. **登录平台确认**设备类型、优化/采样配额余额与有效期；当前设备为 UNVERIFIED，配额为用户口述。
3. **生成英文版论文**：正文、图表、页眉全部英文；建议用现有 `figures/f_*_en.png` 替换中文图。
4. **按规范命名**：论文 `Dapmcm26306844.pdf`。
5. **准备承诺书**：全员签名后扫描为 `Dapmcm26306844cns.pdf` 或 `.jpg`。
6. **打包支撑材料**：`Dapmcm26306844fj.zip`（或 `.rar`），包含程序、结果与说明，排除官方原始数据。
7. **补全附录源码**，或确认支撑材料中的源码满足规范要求。
8. **统一 AI 使用披露**：将预研与工程阶段记录合并为提交用单份说明。
9. **核对并修正论文数字差异**（第 5.1 节），经全队确认后再定稿。
10. **审查并合并 PR #3**；PR #3 已合并。后续审查 `engineering/final-quality` 的工程修复，确认后再由本人决定是否合并。
11. **任何真机提交前**，由账号持有人在本机授权并书面确认任务数、矩阵规模与预计消耗。

---

## 7. 本阶段边界声明

- 未提交任何真机任务，未消耗任何算力配额。
- 未记录、未打印、未提交任何账号、密码、`sdk_code` 或 Token。
- 未修改数学模型、算法、参数、随机种子、QUBO 系数与科学结论。
- 未代写论文正文、未改写研究结论；PR #3 的合并在 Phase 10 由用户明确指示后执行；未自动提交比赛作品。

---

## 8. Phase 10 最终质量冲刺（2026-11-27）

- 分支：`engineering/final-quality`（基于 `main` @ `a372327`；**未合并、未推送**）
- 配套文件：`CODE_AUDIT.md`、`QUALITY_TEST_REPORT.md`、`CHANGELOG.md`
- 边界：未提交真机任务、未消耗配额、未保存凭据、未改模型与科学结论

### 8.1 已完成

| 项目 | 状态 | 证据 |
|---|---|---|
| P0 未知阶段失败分类 | PASS | `unknown_failure` 计配额并拦截重复；`test_unknown_failure_is_conservative` |
| P1 授权/构造失败可重试 | PASS | `submit_failed` + `prepare:*`；`test_backend_prepare_failure_is_retryable` |
| P1 返回解格式校验 | PASS | 列数/±1/空解；3 个入口统一校验；`test_invalid_solution_shape_rejected` |
| P1 旧输出覆盖保护 | PASS | 写入前生成 `*.bak-时间戳`；`test_backup_if_exists_preserves_old_output` |
| P1 采样参数可追溯 | PASS | `sample_number_param` / `returned_solutions`；`test_dry_run_separates_requested_and_returned_samples` |
| P1 README 脚本数 | PASS | 15 → 20 |
| 自动化测试 | PASS | 16/16，3.553 s |
| 工程自检 | PASS | kaiwu-verify：PASS 15 / FAIL 0 / WARN 1；kaiwu-original：PASS 15 / FAIL 0 / WARN 0 |
| Gate 2 实验记录 | PASS（任务级） | 3 个任务 ID/设备/时长/解数/合法数与 PDF 一致；27 个解向量 H 最大偏差 0.000 |
| 历史实验产物 | PASS | 未改写 `results/` 历史文件 |

### 8.2 必须关闭的阻塞项（交参赛队员）

| # | 阻塞项 | 状态 |
|---|---|---|
| 1 | A1 Hamiltonian 排序方向与图注 | 待确认（`CODE_AUDIT.md` 第 3 节） |
| 2 | A2 退火 ΔH 系数与温度定义 | 待确认 |
| 3 | A3 辅助自旋/变量名解码方式 | 待确认 |
| 4 | A4 分辨率口径统一 | 待确认 |
| 5 | A5 “金标准”术语改为“代理模型矩阵精确最优” | 待确认 |
| 6 | A6 优化模式 sample_number 文案 | 待确认 |
| 7 | 论文元数据 5 处差异（第 5.1 节） | 待修正 |
| 8 | 英文版论文、命名、承诺书、支撑材料 | 待完成 |
| 9 | 传递依赖清单（可选） | 待提供 |
| 10 | 任何新的真机实验方案与配额分配 | 待本人书面授权 |

### 8.3 最终交付条件

工程侧已满足：无未处理 P0、必要 P1 已关闭、数学/术语问题已移交、16/16 测试通过、历史产物未覆盖、dry-run 安全、源码可追溯至输入版本（后续任务）。

仍不满足：论文元数据与英文版等提交材料由参赛队员完成；历史三次任务缺少当时的输入哈希（已标记 PARTIAL，不补造）。

满足以上人工事项后，可停止工程开发，不再开启新阶段。

