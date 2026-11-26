# AI 使用记录（AI_USAGE_LOG）

> 用途：按竞赛合规要求，记录 AI 在本次预研中的实际参与范围，便于在论文/支撑材料中如实披露。
> 原则：AI 只做环境搭建、资料核查、通用教学案例、代码调试与文档整理；**未参与 D 题核心模型、算法设计、求解与结论**。

---

## 1. 本次预研的 AI 参与范围

| 允许（已做） | 禁止（未做） |
|---|---|
| 抓取并核对官方文档、版本、API 签名 | 设计 D 题模型或算法 |
| 创建独立 Python 环境、安装 SDK | 代替队员求解正式赛题 |
| 编写并运行通用教学案例（整数划分/背包/TSP/最大独立集） | 生成论文正文或研究结论 |
| 调试 SDK 报错、修正 API 用法 | 伪造真机结果 |
| 整理报告、日志、复现脚本 | 记录或传播账号密码/Token/sdk_code |

---

## 2. 操作流水（2026-11-26）

| 时间 | 操作 | 工具/命令 | 结果 | 产出 |
|---|---|---|---|---|
| 11:47 | 检查工作目录 | `Get-ChildItem` | 目录为空，无官方教程/附件 | 记录于 `references/README.md` |
| 11:47 | 采集硬件信息 | `Get-CimInstance` | Win10 19045 / i5-12600KF / 63.8GB / RTX4060 | 写入 SDK 报告 |
| 11:48 | 探测网络 | `Invoke-WebRequest` | 文档站 200、PyPI 200、平台 28ms | 记录 |
| 11:48 | 抓取官方文档 | WebFetch | 安装说明、Changelog、FAQ、精度、模式、CIM 模块 | 差异表素材 |
| 11:48 | 查询 PyPI 元数据 | `pypi.org/pypi/kaiwu/json` | 最新 1.4.4，支持 3.10/3.12/3.14 | 版本结论 |
| 11:49 | 创建独立环境 | `py -3.12 -m venv environment\.venv` | Python 3.12.6 | `environment/.venv` |
| 11:49 | 安装 SDK | `pip install kaiwu==1.4.4` | 成功，自动装 kaiwu-community 1.0.8 | `logs/phase1_pip_install.log` |
| 11:49 | 首次求解探测 | `SimulatedAnnealingOptimizer.solve` | 触发 license 输入，EOF 失败 | 确认 SA 需授权 |
| 11:50 | API 签名探针 | `inspect.signature` | 修正旧教程中的错误 API | `tests/api_probe.py` |
| 11:52 | Phase 2 教学案例首跑 | `qubo_teaching_cases.py` | 4 案例 FAIL（漏 offset / 符号约定） | 定位问题 |
| 11:53 | 修正后复跑 | 同上 | **4/4 PASS** | `logs/phase2_qubo_cases.log` |
| 11:54 | Phase 3 求解器探测 | 子进程 + stdin 关闭 | BruteForce/Tabu/Sampler PASS；SA BLOCKED | `logs/phase3_classical.log` |
| 11:55 | BruteForce 规模测试 | 8–20 bit | 20bit 13.8s，结果与枚举一致 | `phase3_classical.json` |
| 11:56 | SA Sampler 探测 | `.solve()` | 可用（无 license），日志较多 | 记录 |
| 11:59 | license 状态检查 | `kw.license.ensure_license()` | 本机未授权 | `logs/phase1_license_state.log` |
| 12:00 | 环境自检脚本 | `verify_env.py` | PASS（license 除外） | `environment/verify_env_result.json` |
| 12:05 | 生成报告 | — | 6 份文档 + README + AGENTS | `docs/` |

---

## 3. 人工确认点（必须由队员完成）

| # | 事项 | 时间要求 | 负责人 | 状态 |
|---|---|---|---|---|
| 1 | 确认本届竞赛对 AI 工具的具体规定 | 11-26 晚 | 队长 | 待办 |
| 2 | 登录平台、初始化 license | 11-27 12:00 前 | 队长 | 待办 |
| 3 | 确认算力配额与机型 | 11-27 12:00 前 | 队长 | 待办 |
| 4 | 授权首次真机提交 | 11-27 18:00 前 | 全队 | 待办 |
| 5 | 复核本文件内容真实性 | 11-26 晚 | 队长 | 待办 |
| 6 | 决定是否在论文中披露 AI 使用 | 11-29 前 | 全队 | 待办 |

---

## 4. 披露模板（供论文/支撑材料使用，需人工改写）

> 在本次竞赛中，参赛队使用了 AI 编程助手辅助完成开发环境搭建、官方文档核对、SDK 通用教学案例的调试与实验日志整理。AI 未参与赛题模型设计、算法方案选择、结果解释与研究结论的形成。所有由 AI 辅助生成的代码均经队员实际运行验证；全部实验命令、日志与结果保存在支撑材料中，可复现。AI 工具的使用符合本届竞赛规则的要求。

请队长在提交前核对上述表述是否与本届规则一致，并据实修改。

---

## 5. 记录维护规则

1. 每次使用 AI 做实质性操作（写代码、改配置、查资料），在本表追加一行。
2. 只记录"做了什么、用什么、结果如何"，不记录账号密码、Token、sdk_code。
3. 日志文件保留原始输出，不删改；失败记录同样保留（体现真实过程）。
4. 比赛结束后，本文件随支撑材料一并归档。
