# AI 使用记录（Phase 8–9：工程修复、独立复现与版本冻结）

> 用途：按竞赛合规要求，记录 AI 在本阶段的实际参与范围，便于在论文/支撑材料中如实披露。
> 原则：AI 只做环境复现、工程可移植性修复、提交安全加固、记录归档与文档整理；
> **未参与 D 题核心模型、算法设计、QUBO 系数、求解与科学结论**。

- 记录时间：2026-11-27（Asia/Shanghai）
- 工作分支：`engineering/reproducibility`
- Pull Request：#3 <https://github.com/Gay-wushuang/kaiwu/pull/3>（未自动合并，待队友审查）
- 对应验收记录：`docs/ENGINEERING_ACCEPTANCE.md`
- 依据：上一阶段本地 `ENGINEERING_ACCEPTANCE.md` 的验收结论

---

## 1. AI 参与范围

| 允许（已做） | 禁止（未做） |
|---|---|
| 读取验收记录与仓库代码，建立独立分支 | 设计或修改代理模型、目标函数、QUBO 系数 |
| 用 `pathlib` 统一资源路径、补缺失文件报错 | 修改训练参数、随机种子、数学公式 |
| 为真机脚本增加 dry-run、二次确认 | 提交真机任务、消耗算力配额 |
| 移除命令行凭据参数、改为本机交互授权 | 记录、打印、提交任何账号凭据 |
| 建立真机实验索引与 SHA256 清单 | 伪造实验记录或把推测值写成实测值 |
| 修正 README 重复内容与脚本数量 | 修改论文研究结论或替队员做数据分析 |
| 运行本地非真机验收（自检、dry-run、哈希校验） | 自动合并 Pull Request |

---

## 2. 操作流水（2026-11-27）

| 顺序 | 操作 | 工具/命令 | 结果 | 产出 |
|---|---|---|---|---|
| 1 | 同步远程、核对工作区 | `git fetch` / `git status` | `main` 与 `origin/main` 一致 | 无改动 |
| 2 | 创建工程分支 | `git checkout -b engineering/reproducibility` | 成功 | 独立分支 |
| 3 | 修复硬编码路径 | `code/paths.py` + 11 个脚本 | 盘符路径与 `sys.path.insert` 清零 | 可移植 |
| 4 | 真机安全加固 | `d_submit_cim.py` / `d_run_stats.py` | dry-run 默认、二次确认、凭据参数移除 | 安全入口 |
| 5 | 修正 README | — | 删除 3 处重复章节，脚本数改为 15 | 文档一致 |
| 6 | 建立实验索引 | — | 3 个任务 + 1 次失败提交 | `results/EXPERIMENT_INDEX.md` |
| 7 | 生成哈希清单 | Python `hashlib` | 43 个文件 | `results/ARTIFACT_SHA256.json` |
| 8 | 工程验收自检 | `python code/verify_project.py` | PASS 14 / FAIL 0 / BLOCKED 2 / WARN 1 | 见验收记录 |
| 9 | dry-run 安全验证 | `d_run_stats.py ... --dry-run` | 未触发 license、未建任务 | 日志记录 |
| 10 | 非交互提交拦截验证 | `--submit` + 关闭 stdin | 二次确认处中止 | 日志记录 |
| 11 | 凭据扫描 | 工作区 + Git 历史检索 | 未发现明文凭据 | 见验收记录 |
| 12 | 官方数据核验 | 对比 `sha256_public.json`、行数、列数 | 8/8 哈希与行数一致 | 见验收记录 2.2 |
| 13 | 端到端复现 | 临时副本 `python code/run_all.py` | 成功，74 s；与仓库结果有版本差异 | 见验收记录第 11 节 |
| 14 | 论文规范核对 | 读取官方提交规范 PDF、Control/Summary Sheet | 发现语言、命名、承诺书、支撑材料等不合规项 | 见验收记录第 12 节 |
| 15 | 依赖锁定 | `pip freeze` | CPython 3.12.6，54 个包 | `requirements.lock.txt` |
| 16 | 实验版本清单 | 汇总代码/数据/依赖/种子/产物哈希 | 覆盖原始实验与独立复现 | `results/EXPERIMENT_VERSION.json` |
| 17 | 实验归档隔离 | 复制复现输出到独立目录 | 原始 `results/` 未被覆盖 | `results/reproduction_20261127/` |
| 18 | PR 最终验收 | 审查 `main...HEAD` 差异、dry-run、非交互拦截、忽略规则 | 模型参数/公式无改动；安全项 PASS | 见 `RELEASE_CHECKLIST.md` |
| 19 | 英文论文核查 | 检索仓库英文版、解析 PDF/DOCX 内嵌图 | 无英文版；论文嵌入中文图；存在数字不一致 | 见清单第 5 节 |
| 20 | 真机准备 | license 探测；用户本机交互初始化；向用户确认设备/配额 | license 已初始化，`verify_license(27)` 通过；设备未登录确认；配额自述 ≥3 次 | 见清单第 4 节 |

---

## 3. 人工确认点（必须由队员完成）

| # | 事项 | 状态 |
|---|---|---|
| 1 | 补齐赛题附件 8 个 CSV 到 `date/` | 已完成（SHA256 校验通过） |
| 2 | 提供原始实验环境的依赖版本清单 | 待办（阻塞双环境差异核对） |
| 3 | 登录平台确认设备类型、配额余额与有效期 | 待办 |
| 4 | 确认论文表 15 的硬件时长/机型口径与 gap R² 数字 | 待办 |
| 5 | 产出英文版论文、英文图表、合规页眉与文件名 | 待办 |
| 6 | 准备承诺书签名件与支撑材料压缩包 | 待办 |
| 7 | 授权任何新的真机提交 | 待办 |
| 8 | 审查并合并 `engineering/reproducibility` PR | 待办 |
| 9 | 复核本文件内容真实性并形成提交用统一披露 | 待办 |

---

## 4. 披露模板（供论文/支撑材料使用，需人工改写）

> 在本次竞赛中，参赛队使用了 AI 编程助手辅助完成独立环境的工程复现、代码路径可移植性修复、真机提交安全机制加固、实验记录索引与工程验收。AI 未参与赛题模型设计、算法方案选择、QUBO 系数设定、结果解释与研究结论的形成。所有由 AI 辅助修改的代码均经队员实际运行验证；全部实验命令、日志与结果保存在支撑材料中，可复现。AI 工具的使用符合本届竞赛规则的要求。

---

## 5. Phase 10 追加记录（2026-11-27）

### 5.1 参与范围

| 允许（已做） | 禁止（未做） |
|---|---|
| 审计分支、PR、脚本数据流与真机返回格式 | 设计或修改模型、算法、QUBO 系数、参数与种子 |
| 新增输入版本管理、任务归档、配额账本与模拟测试 | 提交真机任务、消耗配额、选择实验方案 |
| 用教学矩阵与模拟后端验证安全属性 | 把模拟结果写成真机结果 |
| 记录数学口径疑点与证据，不修改代码 | 替队员判定公式对错或修改研究结论 |
| 编写运行说明与工程报告 | 自动合并 PR、自动提交比赛作品 |

### 5.2 操作流水

| 顺序 | 操作 | 结果 |
|---|---|---|
| 1 | 读取远程 PR #3、分支差异、评审与检查状态 | OPEN / MERGEABLE / CLEAN，无评审、无 CI |
| 2 | 阅读 15 个既有脚本与验收文档 | 完成数据流与接入能力审计 |
| 3 | 反编译/反射 SDK 转换、能量与任务接口 | 确认辅助自旋位置、`H=-sᵀJs`、任务身份与查询接口 |
| 4 | 核对两份真机逐样本 CSV | 合法解均位于 H 最小端，发现图注方向不一致 |
| 5 | 推导退火 ΔH | 代码系数为精确值的一半，记录待核验 |
| 6 | 实现输入版本管理、任务归档、配额账本、模拟后端 | 新增 6 个模块与 1 个测试文件 |
| 7 | 运行 9 项自动化测试 | 全部 PASS |
| 8 | 运行 `verify_project.py` | PASS 15 / FAIL 0 / BLOCKED 0 / WARN 1 |
| 9 | CLI 冒烟（真实输入，仅 dry-run） | 1.87/2.00 档，未创建任务、未消耗配额 |
| 10 | 撰写 `docs/PHASE10_REPORT.md` | 含修改清单、测试记录、未解决问题、运行说明与合并评估 |

### 5.3 边界声明

- 本阶段 0 次真机提交、0 配额消耗、0 凭据记录。
- 发现的 H 方向与 ΔH 系数问题只报告证据，未修改既有代码与论文数字。
- 新增测试全部使用非赛题教学矩阵与本地模拟后端。

---

## 6. Phase 10 补充：原始实验环境对齐（2026-11-27）

### 6.1 参与范围

| 允许（已做） | 禁止（未做） |
|---|---|
| 原样归档队友提供的 3 份材料并计算哈希 | 修改材料内容或补造缺失信息 |
| 按 `requirements.txt` 建立独立 Python 3.12.5 环境 | 修改、降级或覆盖 `kaiwu-verify` 及其 License |
| 对比依赖、检查导入与 `pip check` | 修改模型、算法、参数、随机种子 |
| 生成 `pip freeze` 锁定与复现说明 | 代替队员执行正式实验或解释数值差异 |
| 区分三种评价口径并写明引用规则 | 把 OOF 或公开池指标写成论文指标 |
| 更新版本清单与发布检查表 | 提交真机任务、消耗配额 |

### 6.2 操作流水

| 顺序 | 操作 | 结果 |
|---|---|---|
| 1 | 归档 `REPRO_NOTES.md` / `requirements.txt` / `same_protocol_metrics.json` | 3 份原样保存，SHA256 记录于 `MANIFEST.json` |
| 2 | 对比队友直接依赖与 `requirements.lock.txt` | 9 项：6 项一致，numpy / scikit-learn / scipy 版本不同，lightgbm 旧环境未装 |
| 3 | 创建独立 CPython 3.12.5 环境 | Anaconda 自带 3.12.5 的 `pyexpat` 加载被拒，改用 uv 独立解释器，未修改 Anaconda |
| 4 | 安装队友 `requirements.txt` | 全部成功，`pip check` 无冲突 |
| 5 | 导入检查 | 10/10 模块 OK；kaiwu 1.4.4（`kw.__version__` 为 1.0.8） |
| 6 | 生成 `pip freeze` | 55 项，`requirements.freeze.txt` |
| 7 | 保护 `kaiwu-verify` | `pip freeze` 与原锁文件逐包一致，未被改动 |
| 8 | 准备复现目录与脚本 | `reproduction/original_env_20261127/`，临时目录运行、不覆盖历史产物 |
| 9 | 区分评价口径 | `docs/reproduction/PROTOCOLS.md`：02→03 / 分组 OOF / 04 盲测 |
| 10 | 更新版本清单与发布检查表 | `EXPERIMENT_VERSION.json`、`RELEASE_CHECKLIST.md` |
| 11 | 在 `kaiwu-original` 执行正式复跑 | 20.8 s 成功；指标与 3.12.6 独立复现完全一致；三个交付文件逐字节一致；仓库历史产物未改动 |

### 6.3 边界声明

- 操作系统无法匹配：队友 Windows 11，本机 Windows 10 19045；未宣称环境完全相同。
- 未提交真机任务、未消耗配额、未读取或记录任何凭据。
- 已执行一次正式复跑（临时目录），只做机械比对；未解释数值差异、未修改研究结论。
- 数值差异只记录，不归因、不修改研究结论。

## 2026-11-28 第二轮研究辅助记录（北京时间）

- 工具为 OpenAI Codex。本次提示中指定 GPT-6.2 Astra、xhigh，实际运行型号和推理档位以会话元数据为准。
- 队员要求解释有限精度下的目标差异，限定使用非赛题教学示例，并将正式方案、参数和逐任务提交确认留给队员。
- 本次核对本地 `main` 提交 `1c09429ee1b89a8db00ec382cd4ee70235453674`，阅读指定报告、决策记录、代码、测试和任务归档。按仓库数值哈希算法读取第一轮 5 个完成任务和 1 个提交前失败记录的归档量化矩阵，均与各自登记的提交矩阵哈希相符。5 个完成任务归档的返回向量末位均为 +1。
- 查询 Kaiwu 官方精度说明与 CIM 接口，核对本机 kaiwu 1.4.4 接口说明，离线执行已有的 5 个教学接口测试，均通过。在“两盏灯恰开一盏”的独立教学例子中，本机 SDK 将三条耦合从 (−50, 0.220, 0.198) 适配为 (−127, 1, 1)，两个合法状态的能量从 −100.044 和 −99.956 变为并列 −254。回复说明了 one-hot 罚项、辅助自旋规范、合法最优与全空间基态的区别。
- 队员尚未给出第二轮正式参数。本次正式 dry-run 和真机提交次数均为 0，配额消耗为 0，平台余额未查询。队员对教学说明的核验、采纳和修改情况待队员据实补记。关键提示与完整回复见本次会话。
- 核验资料见 [Kaiwu 参数精度](https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/precision.html)、[CIMOptimizer 接口](https://kaiwu-sdk-docs.qboson.com/zh/latest/source/modules/kaiwu.cim.html) 和 [APMCM 参赛规则通知](https://apmcm.org/detail/2513?language=cn)。

### 同日追加：执行接口

队员要求用既有入口接收自行确定的第二轮配置。Codex 在 `plan` 和 `run` 接入单任务 JSON，预演显示原始输入、实际目标、原始 Ising、提交矩阵及变量顺序的完整 SHA-256；配置可携带预期哈希。归档增加变量顺序哈希、来源清单和提交矩阵回读核验。真机执行保留逐任务人工确认。只读核验了 4 个已登记的基线 B 输入，并在临时目录用模拟后端或替身验证流程，执行接口测试 23 项通过。正式研究参数由队员提供，本次正式预演、真机提交与配额消耗均为 0。

### 同日追加：量化保真研究辅助

按队员要求，Codex 只查阅现有罚项和精度适配代码及 Kaiwu 官方文档，给出直接取整的步长近似、合法指派集合与排序的比较口径、合法与非法最低能量的间隔，并用非赛题两灯例子手算不同罚项强度的效果。正式方案、参数、求解和结论由队员完成。本次仅追加使用日志，正式预演、真机提交和配额消耗均为 0。队员的核验、采纳及修改情况待据实补记。关键提示与回复见本次会话。[Kaiwu 精度说明](https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/precision.html) · [预处理接口](https://kaiwu-sdk-docs.qboson.com/zh/latest/source/modules/kaiwu.preprocess.html)

## 2026-11-28 第一轮真机执行与项目接管记录（Trae）

- 工具为 Trae 编程助手；会话模型标识为 DeepSeek-V4.1-Flash，实际型号与推理档位以会话元数据为准。
- 在队员明确授权、确认五组合法指派枚举结果，并选择“由执行脚本在 PTY 中回填任务编号”的确认方式后，AI 使用既有 `code/d_experiment.py run --submit` 逐条提交 5 个预先确定的基线 B 配置（B_Q2_baseline、B_Q2_m3x、B_Q2_k8、B_Q3_O3_baseline、B_Q3_FO2_baseline）。AI 未选择或修改模型、算法、QUBO 系数、topk、mfactor、采样数；未执行 Q3 NO2；未重复提交。
- 5 次优化任务全部 completed，消耗 5 次配额；另有 1 次因本机缺少 license 在提交前终止的尝试（submit_failed，0 配额，无云端任务），记录保留。
- 执行环境为 `kaiwu-original`（kaiwu 1.4.4 / Python 3.12.5）。因该环境缺少 `license.lic`，经队员同意复用本机 `kaiwu-verify` 中已有、且验证支持 27 比特的 license 文件；AI 未读取、输入或记录 user_id/sdk_code。
- AI 将平台返回的原始解向量、能量、提交矩阵、变量映射、平台 PDF、设备与硬件耗时归档到 `experiments/tasks/<task_id>/`；逐任务按 `H=-sᵀJs` 复算能量并与平台结果比对，5 组全部一致；平台 PDF 内解向量与归档逐位一致。AI 依据归档数据生成 `results/ROUND1_REAL_MACHINE_REPORT.md`，未替队员解释科学含义。
- 平台报告下载时，队员本人完成平台登录；AI 仅按任务名选择并下载报告，未进行提交、配额或账户变更。
- 项目接管核对：本地与远程 `main` 均为 `17683352876c7d736919534b5ed34d32be418b36`；按队员指定聚焦五个文件；用 `d_experiment.py status` 确认第一轮 5 个完成任务与 1 个失败尝试均在。本次接管未做 dry-run、未提交真机、配额消耗 0。
- 第二轮正式参数尚未由队员给出；AI 未预设方案。后续仅按队员确定并人工确认的配置调用既有入口，保留逐任务人工确认。
- 队员对第一轮结果、报告及本记录的独立核验、采纳与修改情况待据实补记。

## 2026-11-28 任务 001：第一轮成果交付冻结（Trae + Codex）

- Trae（会话模型标识为 DeepSeek-V4.1-Flash）按队员指定范围整理基线 B 模型复现记录、四个预测池、第一轮 5 个完成任务与 1 个失败记录、平台 PDF、配额账本与 AI 使用记录；生成候选包清单、引用关系、来源完整性对照与待确认事项。未修改原始报告或实验数据，未选择研究参数，未提交真机，量子配额消耗 0。
- Codex（`gpt-6.2-sol` / `medium`）作为独立审查 Agent，仅检查候选包目录与交付清单。前三次使用 `read-only`，每次调用的 status、findings、evidence、required_changes 见交付目录 `results/support_materials_candidate_20261128/REVIEW/CODEX_REVIEW_01..03.json`。队员先例外授权第三次复审；第三次仍为 REVISE 后，明确要求 Codex 直接修复。第 4 次调用改用 `workspace-write`，仅允许修改候选包内文件，未改动任何文件并返回 PASS，记录见 `CODEX_REVIEW_04.json`。Trae 按有效反馈修复实际交付问题，并做本地哈希与清单复核。
- 两个 Agent 均未参与核心建模、算法设计、求解方案或科学结论；论文负责人仍需按 `PENDING_CONFIRMATIONS.md` 独立核验。

## 2026-11-28 T002 第一阶段：有限精度目标保真与约束有效性

- Trae（DeepSeek-V4.1-Flash）在队员指定范围内读取数学接口代码、测试、第一轮报告与相关任务归档；运行 `tests/test_math_interfaces.py`（5/5 PASS），执行非赛题 3×3 教学探针，机械复核第一轮 5 个任务的返回向量、合法性与原始/量化最优集合；生成 `results/round2/phase1_math_interfaces/` 证据。未训练模型、未修改第一轮数据、未提交真机，量子配额消耗 0。
- Codex（`gpt-6.2-astra` / `xhigh` / `read-only`）调用 2 次。第一次核验为 REVISE：指出 `M0` 不能对任意非负 V 保证合法解胜出、`resolution` 不能单独决定排序、第一轮复核需列出全部返回样本；Trae 补全证据并修正表述。第二次核验为 CONFIRMED，确认上述修正、48/11/合法命中口径、原始 argmin 保留 2/5 与返回命中 0/5 的区分、合法子空间边界。两次结论见 `results/round2/phase1_math_interfaces/codex_review_01/02.json`。
- 第二轮正式研究配置未提供，第二阶段停止；未选择参数、未执行真机、未消耗配额。

## 2026-11-28 T002-A：有限精度 QUBO 数学表达研究辅助

- 分支：`research/qubo-refinement`（起始 `b4ed23f6cbaa233e70fba20eb369807bc7cf1a6d`）。
- Trae（DeepSeek-V4.1-Flash）阅读允许范围内的数学接口、T002 证据与公开文献种子；向 Codex 提出四个方向的数学问题；独立复算 Codex 的教学例子与命题（33/33 PASS）；核验 5 篇文献的 arXiv/DOI；归档 `results/round2/qubo_refinement/`。未训练模型、未修改基线 B、未提交真机、量子配额消耗 0。
- Codex（`gpt-6.2-astra` / `xhigh` / `read-only`）调用 1 次，输入为问题、上下文和文献种子，未扫描整个仓库；输出罚项阈值、目标变换、替代编码、量化误差四部分的公式、推导、反例与 3 个手算例。Trae 复算未发现需要追加第二次调用的实质性矛盾。
- 本阶段只产出数学研究辅助资料；编码、罚项、变换、评价指标与正式实验参数由队员独立决定，第二阶段工程实现未启动。

## 2026-11-28 T002-A V2：合成编码基准

- Trae（DeepSeek-V4.1-Flash）在 `research/qubo-refinement` 上实现非赛题合成基准：200 个随机 4×4 成本表，one-hot vs domain-wall，strong/weak 两档 M；全逻辑空间穷举并走 8bit 适配；归档 `results/round2/qubo_refinement/EXPERIMENTS/`。未使用赛题输入、未修改第一轮数据、未提交真机、量子配额消耗 0。
- Codex（`gpt-6.2-astra` / `xhigh` / `read-only`）调用 1 次，返回 REVISE：修正 Spearman 常量秩、weak 有效计数，并给出 domain-wall 强罚项反例（`M=4.2` 时非法码 `(010,010)` 能量 −2.6，低于合法最优 1.0）。Trae 已修正实现/README 并复现反例；本次没有追加第二次 Codex。
- 该基准是合成验证，不是正式第二轮实验；编码/参数/验收仍由队员决定。
- 追加冻结 B 输入 topk=8 全空间对照：one-hot 与 domain-wall 在 Q2/O3/FO2 上互有胜负，无跨输入稳定占优；未产生可提交真机的候选，真机 0 次、配额 0。
- 追加 one-hot 罚项缩放候选：B-Q2-NO2 topk=8，M0 本地保留 0、非原始 5、分辨率 3；`lowM=1.05*max V`（mfactor 0.33826009024559534）本地保留 1、非原始 0、分辨率 7.10/7.00、量化约束有效。已生成 `REAL_MACHINE_CANDIDATES/B_Q2_k8_lowM.json` 并 dry-run（未调用 license、未提交、配额 0），等待真机授权。
- 队员授权后提交 `B_Q2_k8_lowM` 1 次：task `t20261128-043036-b_q2_k8_lowm-34f84ed6`，返回 10、合法 2，最低合法 La-Zr（H=−1716，V=0），原始/量化最优命中 1/1；设备 SPQC-1，硬件 4.3098 ms，端到端 7.754 s；平台 PDF 已归档；配额已用 6、剩余 26。未重复提交。

## 2026-11-28 T002-A V4：one-hot 有限精度稳定性验证

- Trae（DeepSeek-V4.1-Flash）在 `research/qubo-refinement` 上完成 3 输入 × 14 个 `M/Vmax`（42 点）全逻辑空间穷举与量化误差结构分析；新增 1.075 点；区分“基态合法”与“全体合法态严格分离”；修正目标块比较、`diff_count` 口径与辅助位取最小能量；在 `code/d_experiment.py` 增加 `adapt_precision`/`precision_method` 接口边界（默认 `direct_8bit`，不改变矩阵与哈希）。23 项实验管线测试与 5 项数学接口测试通过。未选择正式方案、未提交真机、量子配额消耗 0。产出 `results/round2/qubo_refinement/ONEHOT_STABILITY.md` 与 3 个 JSON。
- Codex（`gpt-6.2-astra` / `xhigh` / `read-only`）调用 1 次，返回 REVISE：独立复算 39 点；补算 1.075 并发现 La-Zr/La-Hf 并列；指出 2.80 保留原始最优但多出并列；给出带符号误差的集合保持判据与 `Δ>2ε` 充分条件，并指出 `np.allclose(atol=0)` 仍保留默认相对容差。Trae 已按反馈修正，本轮无第二次调用。
- 关键结论：42/42 点量化基态合法；但 lowM（1.05）的全体合法态分离裕量为 −4，非法态可优于部分合法态；Q2 集合相等只在 1.05/1.10 两个孤立点，1.075 即并列；原始最优间隙 0.001396 远小于量化残差摆动，不能外推为普遍适用。
- 本阶段真机 0 次、配额 0；账面剩余 26，平台余额待核实。

## 2026-11-28 T003：PrecisionReducer 接管与工程融合

- 分支：`research/precision-reducer`（起点 `c001b08`）。
- Trae（DeepSeek-V4.1-Flash）核验本机 Kaiwu 1.4.4 PrecisionReducer 接口与行为；
  实现 `code/precision_reducer.py`、`d_experiment.py` 的 `precision_reducer` 路线、
  扩展归档与 resume；新增 4 项回归测试，全套 32/32 通过；direct8 已知提交矩阵哈希不变。
- 数学与本地验证（非真机）：Q2 lowM 的 PrecisionReducer 扩展 62/121/246 自旋；
  拆分映射用公开 split 接口复现并核验（常数比例偏差 1.4e-14）；截断位宽全空间枚举
  表明最优随位数非单调；SA 拆分一致率 1–10/100，G3/G4 本地弱于 G1/G2。
- Codex（`gpt-6.2-astra` / `xhigh` / `read-only`）调用 1 次，核验可行子空间等价、
  罚项充分性、tp12 的 V=0 来源、截断非单调、映射可区分性与结论边界；输出见
  `results/round2/precision_reducer/EXPERIMENTS/CODEX_REVIEW_01.json`。
- 队员授权“仅提交 tp14”后执行 1 次真机：task `t20261128-161915-b_q2_k8_lowm_pr_tp14-d4f6e0ff`，
  status=completed；扩展 121 自旋；10 返回、拆分一致 2/10、恢复合法 2/10、
  两者同时 1/10，严格有效原始最优命中 1/10（样本 0，La-Zr V=0，H=−206404）；
  平台结果 pkl 与归档扩展解逐元素一致。
- 配额消耗 1（账面已用 7 / 剩余 25）；tp12 未提交；平台 PDF/设备待补。
- 未修改基线 B、第一轮数据与 T001 冻结材料。






