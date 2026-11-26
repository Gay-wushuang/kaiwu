# 需要人工处理的事项（NEXT_ACTIONS）

> 按优先级排列。每项都给出：操作步骤、验收标准、需要回填的信息。
> **红线：不要在任何聊天、文档、Issue、Git 提交中粘贴密码、验证码、Token、`sdk_code`。**

---

## P0-1 提供 D 题题面与附件（阻塞 Phase 6 细化）

**为什么**：当前工作目录为空，没有 D 题 PDF 与数据附件，无法判断数据规模、目标定义与评价方式。

**怎么做**

1. 从竞赛官网/报名系统下载 D 题题面与附件。
2. 放到 `references/`（本题面仅供队内使用，不要提交到公开仓库）。
3. 在工作目录执行：

```powershell
Get-ChildItem references | Select-Object Name, Length
```

**验收标准**：`references/` 下能看到题面 PDF 与全部附件。

**需要回填（非敏感）**

- 附件文件数量、格式、大小
- 数据大致规模（行数/列数/条目数）
- 题目是否明确要求使用量子计算机/真机

---

## P0-2 初始化 SDK license（阻塞 Phase 3 完整验收 + Phase 5）

**为什么**：`SimulatedAnnealingOptimizer` 与 `CIMOptimizer` 都需要 license；当前本机未授权。

**怎么做**

1. 登录 <https://platform.qboson.com/>。
2. 在个人中心/SDK 下载页获取 `user_id` 与 `sdk_code`。
3. 在本机终端执行（**不要把值贴到任何地方**）：

```powershell
cd APMCM2026-D-Feasibility
environment\.venv\Scripts\python.exe -c "import kaiwu as kw; kw.license.init(input('user_id: '), input('sdk_code: ')); print('license init done')"
```

4. 复核：

```powershell
environment\.venv\Scripts\python.exe environment\verify_env.py
```

**验收标准**：输出中 `SimulatedAnnealingOptimizer: PASS`，不再是 `BLOCKED_LICENSE`。

**需要回填**：只回填"成功/失败"和失败报错文本（打码后的），不要回填凭据本身。

---

## P0-3 竞赛页核查（阻塞 Phase 4 账户级资源）

**为什么**：竞赛页需登录，无法确认报名、认证、专属算力。

**怎么做**

1. 打开：
   <https://kaiwu.qboson.com/plugin.php?id=crowdsourcing&modac=contractorCompetitionDetail&modacPage=competitionList&type=competition&taskId=80>
2. 逐项确认并记录"是/否/数值"，填入 `docs/RESOURCE_REPORT.md` 第 3 节。

**需要回填的 8 个问题**

1. 是否需要额外报名？入口链接是什么？
2. 高校学生认证方式？需要哪些材料？审核多久？
3. 竞赛专属算力如何领取？额度是多少？
4. 本账号当前授权状态（已授权/未授权）？
5. 可用真机型号（550 / 1000 / 山海）？
6. 单次任务支持的最大比特数？
7. 每次任务消耗多少额度/次数？
8. 算力有效期到哪天？结果是否支持导出？

---

## P0-4 算力配额与比特预算核对（阻塞选题决策）

**为什么**：设备上限 ≠ 账号配额；FAQ 出现过"100 配额不能提交 550 比特"。

**怎么做**

1. 平台"我的配额/我的算力"截图（只自己留存，不上传）。
2. 按下面公式估一次：

```text
预计比特数 = 决策变量数 + 约束松弛变量数 + 1（Ising 辅助位） + 精度拆分增量
安全线     = 账户单次上限 × 0.8
```

3. 若 `预计比特数 > 安全线`，在 `FEASIBILITY_REPORT.md` 把"硬件容量适配"改判为 FAIL。

**验收标准**：得到一个明确的数字对比（预计 vs 上限）。

---

## P1-1 首次真机教学案例提交（需全队授权）

**为什么**：证明"提交—排队—取结果"闭环真实可用（Phase 5）。

**前置条件**

- P0-2 完成（license 可用）
- P0-4 完成（确认配额足够）
- 队长明确同意消耗 1 次额度

**怎么做（授权后才执行）**

1. 使用官方 5×5 教学矩阵（不是 D 题数据）。
2. 提交前把脚本给队长看一遍，确认矩阵规模与任务数。
3. 记录：任务名、提交时间、排队时长、返回结果、与本地 Tabu 解的差异。

**验收标准**：拿到 1 个真实任务编号 + 结果数组 + 与本地解的一致性对比。

**明确禁止**：未获授权批量提交；用 D 题数据做"试跑"；把任务反复提交刷结果。

---

## P1-2 止损决策（硬性时间点）

| 时间点 | 必须完成 | 未完成则 |
|---|---|---|
| 11-27 12:00 | P0-2 + P0-3 + P0-4 | **转 B 题** |
| 11-28 12:00 | P1-1 真机闭环 | 转 B 题或降级方案 |

决策记录写入 `logs/daily_standup.md`，由论文负责人保管。

---

## P2-1 合规确认

1. 队长确认本届 APMCM 对 AI 工具的官方口径。
2. 确认论文中是否需要披露 AI 使用；如需，使用 `AI_USAGE_LOG.md` 第 4 节模板并人工改写。
3. 确认支撑材料打包内容（代码、日志、结果），不要包含账号信息。

---

## 回填清单（把结果写回文档）

| 信息 | 写回位置 |
|---|---|
| license 是否可用 | `docs/RESOURCE_REPORT.md` 第 3 节 |
| 平台 8 问 | `docs/RESOURCE_REPORT.md` 第 3 节 |
| 配额与比特预算 | `docs/FEASIBILITY_REPORT.md` 第 4 节 C2 |
| 真机任务记录 | `docs/EXPERIMENT_REPORT.md`（新增 Phase 5 小节）+ `logs/` |
| 止损决策 | `logs/daily_standup.md` |
| AI 使用补充 | `docs/AI_USAGE_LOG.md` 第 2 节 |
