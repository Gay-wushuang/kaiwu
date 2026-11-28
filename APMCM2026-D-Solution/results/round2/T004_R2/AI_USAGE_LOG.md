# T004-R2 AI 使用记录

## 1. 实际参与

| 角色 | 模型 | 本轮用途 |
|---|---|---|
| Trae CN | DeepSeek-V4.1-Flash | 前置核验、候选 dry-run、本地预检、提交清单、成本与论文增量、Git |
| Codex | gpt-6.2-astra | **未调用**（额度不足；本轮无重大未解技术错误） |

## 2. Trae 实际完成

1. 核对 HEAD `f07f27f` 与 PR #8 状态（OPEN/CLEAN/MERGEABLE，未合并）。
2. 从 `origin/main` 创建 `research/final-hardware-validation`，FF 到 `f07f27f`。
3. 运行前置验收：33/33 PASS；回归 50/50；基线 B 与 7 任务归档不变。
4. 为 7 个候选生成 dry-run：`FINAL_SUBMISSION_PLAN_DRYRUN.txt`。
5. 本地预检 Q3 direct8 量化保留、PR 构造态可行性与哈希：`R2_CANDIDATE_PRECHECK.json`。
6. 生成 `FINAL_SUBMISSION_PLAN.md`、`CONTROLLED_REPEATS.md`、`COST_SUMMARY.md`、
   `PAPER_DELTA.md`、`FINAL_FREEZE_REPORT.md` 等交接材料。
7. **未提交任何真机任务，未消耗配额，未修改历史证据。**

## 3. AI 没有做的事

- 没有替队员决定候选、参数、设备或科学结论。
- 没有登录平台、核对余额或输入凭据。
- 没有把候选的本地预检写成真机结果。
- 没有将 AI 生成内容冒充队员原创科学成果。

## 4. 待队员确认

1. 平台余额与计费方式。
2. 选择哪些候选并授权提交。
3. 是否执行 G3 / Q3 PR / 重复实验。
4. 论文增量是否采用。
