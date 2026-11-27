# APMCM 2026 D 题 · 第一轮成果支撑材料候选包

- 生成时间：2026-11-28 02:09:01 +0800
- 用途：提交论文负责人审阅的**候选**支撑材料；未正式提交比赛。
- 正式研究基线：**B（独立复现模型 + 预测）**
- 基线 A：仅历史对照，**未收入本包**，禁止与 B 混用。
- 代码时间线：`822b7ea`（B 模型/预测）→ `2a56c55`（第一轮真机）→ `577c83bd013f002df77282538b64185d027ad0c3`（本包基线）。

## 目录

```text
FORMAL/BASELINE_B/     基线 B 模型复现记录、四个预测池、三个交付文件、原始环境对齐记录、P1/P2/P3 口径
FORMAL/ROUND1/         第一轮真机报告、5 个完成任务 + 1 个失败记录、B 输入登记、配额账本、AI 使用记录
DEV_RECORDS/           工程脚本、测试、依赖锁定（非科学成果）
HISTORICAL/            基线 A 历史对照说明（数据不复制）
MANIFEST.csv           包内文件清单（类别/来源/大小/SHA256）
SHA256SUMS.txt         包内 SHA256 校验清单
VERSION.json           基线、模型哈希、任务、配额与排除项
REFERENCE_MAP.md       模型→预测→输入→任务→平台报告的引用关系
KNOWN_ISSUES.md        版本边界与已知问题
PENDING_CONFIRMATIONS.md 待队员确认事项
SECURITY_SCAN.md       凭据/缓存扫描
```

## 基线 B 关键事实

- 模型：`models/surrogate_phys.joblib`，SHA256 `ba22ec9ec9c7555c62d15f4bf543546ad99f2b445f800a25f2cabcd33c300357`，15509867 B；未入包（可重新生成）。
- P1（02→03）：R² `0.824836`，MAE `2.571641`，
  RMSE `4.597198`，Spearman `0.935325`，
  Top-100 `40/100`。
- 交付答案：Q2 `LaZrO2N`（V̂=0.0）；Q3 `PbTiO3`（X=O3，V̂=0.0）。
- 第一轮真机：5 个 `completed` + 1 个 `submit_failed`；设备均为 SPQC-550；配额 5 次，剩余 27。

## 版本与引用边界

1. `V̂` 是代理模型**预测违反度**，不是真实物理违反度。
2. 真机 H 最优是 **8-bit 适配矩阵上的合法 one-hot 最优**，不是全 Ising 空间全局最优。
3. 04 官方盲测集无 `V` 标签，不能本地计算/声称 R²、MAE 等已验证指标。
4. 基线 A 的三次真机报告、`code/predictions/`、`results/cim_*` 均未入包；见 `HISTORICAL/BASELINE_A_REFERENCE.md`。
5. AI 参与范围以 `FORMAL/ROUND1/AI_USAGE_LOG.md` 为准；核心建模、算法、求解与科学结论由队员完成。

## 使用建议

1. 先看 `VERSION.json` 与 `REFERENCE_MAP.md`，确认版本链。
2. 论文引用 B 指标/预测时，只使用 `FORMAL/BASELINE_B/`。
3. 真机结果与平台证据使用 `FORMAL/ROUND1/`，逐任务目录内含原始解、输入、矩阵、PDF。
4. 任何 A/B 数字、`V̂`/物理违反度、合法最优/全空间最优的表述，先按 `PENDING_CONFIRMATIONS.md` 与 `KNOWN_ISSUES.md` 核对。
5. Codex 独立验收记录随仓库交付目录 `results/support_materials_candidate_20261128/REVIEW/` 另存，不放入本 zip，避免验收后改动包体。

## 校验状态

本包生成时已校验：5 个完成任务 + 1 个失败记录存在；B 预测哈希与 `SHA256SUMS` 一致；任务输入哈希与输入登记一致；平台 PDF 存在且哈希匹配；同名 A/B 预测文件哈希不同；包内无 License/凭据/缓存。
