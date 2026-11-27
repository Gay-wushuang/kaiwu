# 原始环境独立复现工作目录

本目录用于让参赛队员在**不覆盖仓库历史产物**的前提下，用队友提供的依赖版本重跑主流程并核验结果。
本目录不包含任何新模型、参数或结论。

- 建立时间：2026-11-27（Asia/Shanghai）
- 对应任务：Phase 10 补充任务 · 原始实验环境对齐
- 环境：`%LOCALAPPDATA%\kaiwu-original`
- 原始材料：`docs/reproduction/original_environment/`
- 口径说明：`docs/reproduction/PROTOCOLS.md`

---

## 1. 环境事实

| 项目 | 队友原始环境（材料声明） | 本次复现环境（实测） | 是否一致 |
|---|---|---|---|
| Python | 3.12.5 | 3.12.5 | 一致 |
| 操作系统 | Windows 11 | Windows 10 企业版 22H2（10.0.19045） | **不一致** |
| 依赖清单 | `requirements.txt`（9 个直接依赖） | 同文件安装 | 一致 |
| 传递依赖 | 未提供 | `requirements.freeze.txt` 实测锁定 | 无法逐包对齐 |

结论：Python 版本可以精确匹配，但**操作系统不同**，不能宣称与队友环境完全相同。
数值复核时应按“同 Python / 同直接依赖 / 不同 OS”的前提解释差异，不把差异单独归因于某一项。

---

## 2. 目录保护约定

- 仓库原有 `results/`、`code/predictions/`、`models/` 一律不覆盖。
- 复现脚本先把 `code/` 与 `date/` 复制到 `%TEMP%\apmcm_repro_original_<时间戳>\`，在该目录内运行。
- 所有输出只写临时工作目录；需要比较时按 SHA256 对照，不把结果拷回仓库。
- `kaiwu-verify` 环境及其 License 保持不变；本复现环境是独立的 `kaiwu-original`。

---

## 3. 运行方式（参赛队员执行）

前置条件：

1. `date/` 下已有官方 8 个 CSV（仓库 `.gitignore` 排除，需自行放置）。
2. 已确认 `%LOCALAPPDATA%\kaiwu-original\Scripts\python.exe` 存在且依赖安装完成。

执行：

```powershell
cd APMCM2026-D-Solution
.\reproduction\original_env_20261127\run_reproduction.ps1
```

指定工作目录或环境解释器：

```powershell
.\reproduction\original_env_20261127\run_reproduction.ps1 `
    -WorkDir "$env:TEMP\apmcm_repro_manual" `
    -EnvPython "$env:LOCALAPPDATA\kaiwu-original\Scripts\python.exe"
```

脚本行为：

1. 校验解释器、`code/`、`date/`；
2. 复制 `code/` 与 `date/` 到独立工作目录（已存在则拒绝，除非显式 `-Force`）；
3. 在工作目录内执行 `python code/run_all.py`；
4. 输出关键产物的 SHA256，供与仓库基线对照。

脚本不会调用 `kaiwu` 真机接口，不提交任务，不消耗配额。

---

## 4. 需要人工核验的产物

| 文件 | 用途 |
|---|---|
| `results/metrics.csv` / `metrics.json` | 代理模型指标（P1 口径） |
| `results/model_compare.csv` | 直接回归与物理量路线对照（P1） |
| `results/submission_q1_holdout.csv` | 问题 1 对 04 盲测集的预测（P3，无本地标签） |
| `results/submission_q2_top20.csv` / `q3_top20.csv` | 问题 2/3 候选排序 |
| `results/final_answers.json` | 机器可读汇总 |

核验规则：

1. 只比较**同口径**指标，口径定义见 `docs/reproduction/PROTOCOLS.md`。
2. 04 盲测集没有 `V` 列，本地不能计算 R²/MAE；只能核对行数、列名与预测分布。
3. 不得把分组 OOF 指标写成论文指标。
4. 不得用公开池标签回算替代 02→03 验证或 04 盲测。
5. 数值差异只记录、不擅自归因；由队员决定是否可接受。

---

## 5. 状态

| 项目 | 状态 |
|---|---|
| 原始材料归档 | PASS（含 SHA256） |
| 依赖差异清单 | PASS（直接依赖） |
| 独立环境创建 | PASS |
| 依赖安装 | PASS（`pip check` 无冲突，10/10 模块导入 OK） |
| 模块导入检查 | PASS（见 `docs/reproduction/original_environment/import_check.json`） |
| 主流程正式复跑 | **PASS**（2026-11-27，20.8 s；指标与 3.12.6 独立复现完全一致，三个交付文件逐字节一致；见 `run_20261127/COMPARISON.md`） |
| 04 官方评分 | 无法本地完成 |
