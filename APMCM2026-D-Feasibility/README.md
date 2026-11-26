# APMCM2026-D-Feasibility

2026 年第十六届 APMCM 亚太地区大学生数学建模竞赛 **D 题（专用量子计算机寻找钙钛矿稀有目标）技术预研仓库**。

本仓库不包含、也不会包含正式赛题的核心模型、算法设计、求解结果或研究结论。它只回答一个问题：

> 我们这支没有量子计算开发经验的三人本科生队伍，在剩余比赛时间内，是否有条件用 Kaiwu SDK + 玻色量子云平台完成 D 题？

---

## 1. 当前状态总览

| 阶段 | 内容 | 状态 | 依据 |
|---|---|---|---|
| Phase 0 | 官方文档、版本、API 变更核查 | **PASS**（D 题附件除外） | 已抓取官方文档站与 PyPI 元数据，见 [SDK_VERSION_REPORT.md](docs/SDK_VERSION_REPORT.md) |
| Phase 1 | 独立环境搭建与 SDK 安装 | **PASS** | Python 3.12.6 独立 venv，`kaiwu==1.4.4` 安装成功并可导入 |
| Phase 2 | QUBO → Ising → 求解 → 解码链路 | **PASS** | 4 个通用教学案例全部与全枚举最优解一致，见 [EXPERIMENT_REPORT.md](docs/EXPERIMENT_REPORT.md) |
| Phase 3 | 本地经典求解器与 8bit 精度工具 | **PASS（部分）** | BruteForce / TabuSearch / SA Sampler 可用；`SimulatedAnnealingOptimizer` 被 license 拦截，标记 BLOCKED |
| Phase 4 | 云平台算力与账户资源核查 | **BLOCKED** | 竞赛页与平台均需登录，未登录前不推测账户状态，见 [RESOURCE_REPORT.md](docs/RESOURCE_REPORT.md) |
| Phase 5 | 真机教学案例测试 | **BLOCKED** | 无 license、无算力授权；未提交任何真机任务 |
| Phase 6 | D 题适配性评估 | **CONDITIONAL GO** | 条件与失败点见 [FEASIBILITY_REPORT.md](docs/FEASIBILITY_REPORT.md) |

> 状态定义：PASS = 实际验证通过；FAIL = 实际验证失败；BLOCKED = 外部阻塞；UNVERIFIED = 尚未验证。
> 本仓库不把"理论上可行"标记为 PASS。
>
> 逐阶段六要素验收明细见 [PHASE_ACCEPTANCE.md](docs/PHASE_ACCEPTANCE.md)；需要人工处理的事项见 [NEXT_ACTIONS.md](docs/NEXT_ACTIONS.md)。

---

## 2. 目录结构

```text
APMCM2026-D-Feasibility/
├── references/                  # 官方资料摘录与来源清单（不含赛题答案）
├── docs/                        # 六份核查/评估报告
├── environment/
│   ├── .venv/                   # 独立虚拟环境（不提交）
│   ├── requirements.txt         # 直接依赖（可复现）
│   ├── requirements.lock.txt    # 全量冻结版本
│   └── verify_env.py            # 环境自检脚本
├── examples/
│   ├── qubo_teaching_cases.py   # Phase 2：四个通用教学案例
│   └── classical_solver_check.py# Phase 3：本地求解器 + 精度工具 + 稳定性
├── tests/
│   └── api_probe.py             # SDK API 签名探针（用于核对文档）
├── experiments/results/         # 机器可读的实测结果 JSON
├── logs/                        # 终端日志（安装、运行、license 状态）
├── reports/                     # 预留：面向团队的汇报材料
├── README.md
└── AGENTS.md
```

---

## 3. 环境复现

要求：Windows 10/11 x64，Python 3.10 / 3.12 / 3.14（实测 3.12.6）。

```powershell
cd APMCM2026-D-Feasibility
py -3.12 -m venv environment\.venv
environment\.venv\Scripts\python.exe -m pip install -r environment\requirements.txt
```

`requirements.txt` 只固定直接依赖；需要逐包复现时使用 `requirements.lock.txt`。

环境自检：

```powershell
environment\.venv\Scripts\python.exe environment\verify_env.py
```

自检会输出 Python 版本、SDK 版本、模块可用性、四个本地求解器的 license 依赖状态。若尚未初始化 license，`SimulatedAnnealingOptimizer` 会被标记为 `BLOCKED_LICENSE`，这是预期结果。

---

## 4. 运行实验

```powershell
# Phase 2：QUBO/Ising 教学案例（无需 license）
environment\.venv\Scripts\python.exe examples\qubo_teaching_cases.py

# Phase 3：经典求解器、8bit 精度适配、稳定性（无需 license）
environment\.venv\Scripts\python.exe examples\classical_solver_check.py
```

两个脚本的退出码为 0 表示该阶段验收通过。结果写入 `experiments/results/*.json`，控制台日志自动保存到 `logs/`。

---

## 5. license 与算力（重要）

- 本地 `BruteForceOptimizer`、`TabuSearchOptimizer`、`SimulatedAnnealingSampler` 实测**无需 license**。
- `SimulatedAnnealingOptimizer` 与 `CIMOptimizer`（真机）**需要 license**，首次调用会提示输入 `user_id` 与 `sdk_code`。
- 获取方式：登录 <https://platform.qboson.com/> → 生成 user_id / SDK 授权码。
- 初始化命令（凭据只在本机执行，不要提交、不要发到聊天里）：

```python
import kaiwu as kw
kw.license.init("YOUR_USER_ID", "YOUR_SDK_CODE")
```

凭据不要写入本仓库任何文件。真机任务会消耗账户算力额度，提交前必须人工确认，详见 [NEXT_ACTIONS.md](docs/NEXT_ACTIONS.md)。

---

## 6. 合规边界

1. 本仓库仅做技术预研，不代替参赛者完成正式赛题的建模、求解与结论。
2. 所有教学案例均与 D 题无关，只用于验证工具链。
3. 未伪造任何真机结果；Phase 5 因无授权记为 BLOCKED。
4. AI 使用过程记录在 [AI_USAGE_LOG.md](docs/AI_USAGE_LOG.md)，便于按竞赛要求披露。
5. 竞赛规则明确禁止向团队成员以外的人寻求帮助，AI 工具的使用边界请队长结合本届规则自行确认并在论文/支撑材料中如实说明。

---

## 7. 关键事实速查

| 项目 | 实测/官方值 | 来源 |
|---|---|---|
| SDK 最新版本 | 1.4.4 | PyPI `kaiwu` 元数据（2026-11-26 查询） |
| 支持 Python | 3.10 / 3.12 / 3.14 | 官方安装说明（latest）+ wheel 标签 |
| Windows 支持 | `win_amd64` wheel，Win10 实测可用 | 实装验证 |
| Ising 系数精度 | 8bit 整数 `[-128, 127]` | 官方"参数精度"页 |
| QUBO→Ising | 自动增加 1 个辅助自旋 | 官方文档 + 实测 3→4 |
| 真机规模 | SPQC-550 / SPQC-1000；山海 1000 最高 3000 | 官方云站公开页面 |
| 公开单价 | 68 元/次（550）、128 元/次（1000） | 官方云站公开页面（竞赛专属额度未核实） |
| 比赛时间 | 2026-11-26 06:00 至 2026-11-30 09:00 | APMCM 官方参赛规则 PDF |
