# references/ — 资料与来源

## 0. 关于"项目目录中的官方教程"

首次检查（2026-11-26 11:47）时，工作目录 `E:\ERE\Documents\Work\开物量子` 为空，**没有**用户提到的以下资料：

- 云平台使用教学
- 不懂量子也能编程！
- Kaiwu SDK 环境配置入门手册
- 如何应用 QUBO 模型来建模
- 竞赛官方规则及 D 题附件

因此本预研的全部信息来自官方在线文档与实际运行，不以旧教程为准。若后续拿到上述资料，请放入本目录，并对照 `docs/SDK_VERSION_REPORT.md` 第 4 节差异表复核。

## 1. 官方在线资料（访问时间：2026-11-26）

| 资料 | URL | 提取到的关键信息 |
|---|---|---|
| 文档站首页/目录 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/> | 模块手册、入门教程、进阶知识结构 |
| 概述 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/getting_started/introduction.html> | 企业版 vs 社区版模块划分；Ising 定义 `H=-ΣJσσ-μΣhσ` |
| 安装说明 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/getting_started/sdk_installation_instructions.html> | Python 3.10/3.12/3.14；从平台下载 whl 的旧流程 |
| Changelog | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/about/changelog.html> | 1.4.4 变更、interval 单位、SA 采样器行为、任务命名规则 |
| TSP 教程 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/getting_started/tsp.html> | `kw.core.ndarray`、`QuboModel`、约束写法、精度拆分示例 |
| Max-Cut 教程 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/getting_started/max_cut.html> | Ising 原生建模与 SA 求解 |
| 真机教程 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/getting_started/tutorial4_cloud_platform_usage_cases.html> | 网页上传与 SDK 调用两条路径 |
| 参数精度 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/precision.html> | 8bit `[-128,127]`；四种降精度方法；辅助自旋 |
| 计算模式 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/mode.html> | Optimization / Sampling，`sample_number` 10–2000 |
| CIM 模块手册 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/modules/kaiwu.cim.html> | `CIMOptimizer` 完整签名与注意事项 |
| 旧版 FAQ | <https://kaiwu.qboson.com/docs/FAQ.html> | 1.3.0 时代说法，用于对照（多处已过时） |
| PyPI 元数据 | <https://pypi.org/pypi/kaiwu/json> | 最新 1.4.4、依赖、wheel 列表 |
| 玻色量子云 | <https://cloud.qboson.com/> | 550/1000/山海 1000 型号、68/128 元公开价 |
| APMCM 参赛规则 | <https://apmcm.org/uploads/files/20261020/1792484391858628.pdf> | 比赛时间 11-26 06:00 至 11-30 09:00；提交要求 |
| 竞赛页（需登录） | <https://kaiwu.qboson.com/plugin.php?id=crowdsourcing&...&taskId=80> | 未能访问，标记 BLOCKED |

## 2. 本地实测证据

| 文件 | 内容 |
|---|---|
| `logs/phase1_pip_install.log` | SDK 安装全过程 |
| `logs/phase1_verify_env.log` | 环境自检结果 |
| `logs/phase1_license_state.log` | license 未授权证据 |
| `logs/phase2_api_probe.log` | API 签名与 QUBO→Ising 实测 |
| `logs/phase2_qubo_cases.log` | 四个教学案例运行结果 |
| `logs/phase3_classical.log` | 求解器、精度、稳定性实测 |
| `experiments/results/phase2_qubo_cases.json` | 教学案例机器可读结果 |
| `experiments/results/phase3_classical.json` | Phase 3 机器可读结果 |

## 3. 使用约定

1. 本目录中的题目/附件（若后续加入）仅供队内使用，不要提交到公开仓库。
2. 引用官方文档时保留 URL 与访问时间，便于论文参考文献核对。
3. 不要把账号、Token、授权码放入本目录。
