# T004 AI 使用记录

本记录只列 T004 实际发生的 AI 参与，不替代 T001/T003 的记录。所有 AI 产出均可由本目录的脚本与
归档复核；核心参赛数学方案、正式参数、真机提交与科学结论由参赛队员决定。

## 1. 角色与模型

| 角色 | 模型 | 权限 | 实际用途 |
|---|---|---|---|
| Trae CN（主控/工程） | DeepSeek-V4.1-Flash | 工作区读写、本地运行 | 读题、核对归档、写审计脚本、运行本地枚举/SA/测试、生成交接材料 |
| Codex（数学核验） | gpt-6.2-astra，reasoning=xhigh | **read-only** | 1 次：核验固定 X 分解、单 QUBO 构造、Z2 对称性、PrecisionReducer 证据边界 |

Codex 调用命令（本地，只读，未写文件）：

```powershell
Get-Content -Raw -Encoding UTF8 EXPERIMENTS/CODEX_REVIEW_T004_QUESTION.md |
  & "C:\Users\ERE.DESKTOP-JD48OPB\AppData\Local\OpenAI\Codex\bin\9e1da79431da526b\codex.exe" `
    exec -m gpt-6.2-astra -s read-only -c model_reasoning_effort="xhigh" -
```

回复：`EXPERIMENTS/CODEX_REVIEW_T004_RESPONSE.md`。**Codex 实际调用 1 次。**

## 2. Trae 实际完成的工作

1. 读取原始题面 `statement/2026_APMCM_Problem_D.pdf`，确认 Q3 的 8,112 候选、三选一 X、
   “model in QUBO form”要求。
2. 建立 `research/final-validation` 分支（从 `main` `306cab7`）。
3. 核对 7 个已完成真机任务的归档：输入矩阵、提交矩阵、原始/扩展向量、PDF、设备、时间、哈希。
4. 编写并运行：
   - `EXPERIMENTS/q3_audit.py`：Q3 全池/固定 X/topk/量化/真机五层证据；Q3 NO2 复用 Q2 输入。
   - `EXPERIMENTS/task_audit.py`：7 个任务的统一合法率、拆分一致率、严格命中、量化集合。
   - `EXPERIMENTS/space_gap_audit.py`：direct8 实例的 2^26 / 2^16 全空间精确枚举。
   - `EXPERIMENTS/route_cost.py`：G1–G4 与 Q3 路线的构造/适配耗时。
   - `EXPERIMENTS/g3_tp14_local.py`：G3 缺格的本地 SA。
   - `EXPERIMENTS/acceptance_check.py`：33 项集中验收。
   - `EXPERIMENTS/make_final_metrics.py`：生成 `FINAL_METRICS.csv`。
5. 运行回归测试：40/40 OK；direct8 已知哈希不变；基线 B 四个预测文件哈希不变。
6. 生成 Q3 证据、受控对照、论文交接、技术冻结与证据映射。
7. 对 3 个候选做 dry-run（`REAL_MACHINE_CANDIDATES/CANDIDATE_PLANS.txt`），**未提交任何真机任务**。

## 3. AI 没有做的事

- 没有替参赛队决定 Q3 的最终代表候选、论文结论或正式研究参数。
- 没有提交真机、没有输入/保存 license 凭据、没有查询平台余额。
- 没有修改基线 B、T001 冻结材料、旧论文或论文负责人正在编辑的文件。
- 没有把 Codex 的数学核验结论当作参赛队原创；Codex 只做独立核验。

## 4. 需要队员确认的 AI 相关事项

1. 论文中如何使用本目录的复算值（尤其基线 A/B 的选择）。
2. 是否引用 Codex 的 208 比特单 QUBO 构造；若引用，应注明“独立数学核验，未提交”。
3. 是否在 AI 使用披露中写明：Trae 负责工程与审计，Codex 负责 1 次数学核验，
   核心方案与结论由队员决定。
4. 三个真机候选是否授权提交；默认不提交。

## 5. 可复核入口

- 机器可读证据：`EXPERIMENTS/*.json`
- 原始控制台：`EXPERIMENTS/*_console.txt`、`REGRESSION_TESTS.txt`
- 验收：`EXPERIMENTS/ACCEPTANCE.json`
- Codex：`EXPERIMENTS/CODEX_REVIEW_T004_QUESTION.md`、`..._RESPONSE.md`
- 指标：`FINAL_METRICS.csv`
- 论文映射：`FINAL_EVIDENCE_MAP.md`、`PAPER_CHANGE_LIST.md`
