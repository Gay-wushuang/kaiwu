# SDK 版本与兼容性报告（Phase 0 + Phase 1）

- 核查时间：2026-11-26（北京时间）
- 核查方式：官方文档站 + FAQ + PyPI 元数据 + 本机实际安装运行
- 核查人：AI 辅助预研（人工复核见 `AI_USAGE_LOG.md`）
- 结论：**SDK 版本与 Windows/Python 兼容性 PASS；"竞赛指定 SDK 版本"因竞赛页需登录，BLOCKED。**

---

## 1. 一句话结论

当前官方最新版为 **Kaiwu SDK 1.4.4**，支持 **Python 3.10 / 3.12 / 3.14**，Windows 提供 `win_amd64` wheel；本机用 **Python 3.12.6 + Windows 10 22H2** 实际安装并跑通建模、QUBO→Ising 转换、本地求解，**兼容性 PASS**。

**不要照抄旧教程**：网上流传的 1.3.0 时代 FAQ 说"仅支持 Python 3.10"、要求从平台下载 whl、使用 `kw.solver.SimpleSolver`，这些说法在当前版本已经不成立或已变更（见第 4 节差异表）。

---

## 2. 版本事实

| 项目 | 实测/官方值 | 来源 |
|---|---|---|
| 发行版包名 | `kaiwu`（企业版） | PyPI 元数据 |
| 最新版本 | `1.4.4` | PyPI `kaiwu` 最新 release |
| 已发布版本 | 1.3.1 / 1.4.0 / 1.4.1 / 1.4.2 / 1.4.3 / 1.4.4 | PyPI release 列表 |
| 依赖 `kaiwu-community` | `1.0.8` | PyPI `requires_dist` |
| Python 要求 | `>=3.10`，官方声明 3.10 / 3.12 / 3.14 | PyPI + 官方安装说明 |
| 平台 wheel | `win_amd64` / `manylinux1_x86_64` / `macosx`（x86_64、arm64） | PyPI 文件列表 |
| 许可证 | 企业版，需要有效 license 才能使用受授权功能 | PyPI 描述 + 实测 |
| 竞赛指定版本 | **未获取**（竞赛页 `taskId=80` 需登录） | BLOCKED |

实测安装命令与结果：

```powershell
py -3.12 -m venv environment\.venv
environment\.venv\Scripts\python.exe -m pip install kaiwu==1.4.4
# Successfully installed kaiwu-1.4.4 kaiwu-community-1.0.8 numpy-2.5.5 pandas-2.2.3 matplotlib-3.10.3 ...
```

安装日志：[phase1_pip_install.log](../logs/phase1_pip_install.log)

---

## 3. 本机环境核查

| 项目 | 实测值 | 判定 |
|---|---|---|
| 操作系统 | Windows 10 企业版 22H2，10.0.19045，x64 | PASS |
| CPU | Intel i5-12600KF，10 核 16 线程 | PASS |
| 内存 | 63.8 GB（可用约 32.9 GB） | PASS |
| GPU | NVIDIA RTX 4060（SDK 不依赖 GPU） | 不影响 |
| Python（系统） | Anaconda 3.12.5 + 独立 3.12.6 | 未改动，符合"不破坏现有环境" |
| 独立环境 | `environment\.venv`（Python 3.12.6） | PASS |
| 网络 | 可访问 PyPI、`kaiwu-sdk-docs.qboson.com`、`platform.qboson.com`（28 ms） | PASS |
| SDK 导入 | `import kaiwu as kw` 成功 | PASS |
| SDK 版本 | `importlib.metadata.version("kaiwu") == 1.4.4` | PASS |
| 模块完整性 | `core/classical/cim/preprocess/sampler/hybrid/hobo/license` 均存在 | PASS |
| 授权状态 | 本机无 license 文件；`kw.license.ensure_license()` 提示输入 user_id | **BLOCKED（未授权）** |

环境自检日志：[phase1_verify_env.log](../logs/phase1_verify_env.log)，
license 探测日志：[phase1_license_state.log](../logs/phase1_license_state.log)。

---

## 4. 新旧文档差异表

> "旧资料"指 1.3.0 时代 FAQ（页面标注最后更新 10/22/25）及网上二次转载教程；"最新"指 1.4.4 官方文档与实测。

| # | 项目 | 旧资料说法 | 最新文档 / 实测 | 影响 | 来源 |
|---|---|---|---|---|---|
| 1 | 最新版本 | "已更新至 1.3.0" | 1.4.4（PyPI） | 旧教程命令、API 可能失效 | 旧 FAQ；PyPI |
| 2 | Python 版本 | "仅支持 Python 3.10" | 3.10 / 3.12 / 3.14 | 3.12 可直接用，不必装 3.10 | 旧 FAQ；官方安装说明；实测 |
| 3 | 安装方式 | 登录平台下载 `kaiwu-sdk.linux.1.4.0.zip`，再 `pip install xxx.whl` | `pip install kaiwu==1.4.4` 即可（企业版已上 PyPI） | 不必找平台下载入口，安装更简单 | 官方安装说明仍写旧流程；PyPI 描述 vs 实测 |
| 4 | 模块数量/名称 | 10 个模块：`cim/classical/common/core/ising/license/preprocess/qubo/sampler/solver` | 9 个：`core/common/hobo/preprocess/hybrid/cim/classical/sampler/license`；**没有 `ising`、`qubo`、`solver`** | 旧代码 `kw.solver.SimpleSolver`、`kw.qubo.*`、`kw.ising.*` 全部报 AttributeError | 旧 FAQ；官方概述页；实测 `hasattr` |
| 5 | `SimpleSolver` | FAQ 给出 `kw.solver.SimpleSolver(optimizer)` 示例 | 该模块不存在；改用 `solver.solve_qubo(qubo_model)` | 旧示例无法运行 | 旧 FAQ；实测 |
| 6 | `SimulatedCIMOptimizer` | 旧教程使用 | 已移除（1.0.3 / 1.2.0）；官方建议用 `SimulatedAnnealingOptimizer` | 旧代码报 AttributeError；替代方案需 license | 旧 FAQ；实测 |
| 7 | `CIMOptimizer` 初始化 | v1.2：`CIMOptimizer(user_id, sdk_code)`；v1.3：`CIMOptimizer(task_name_prefix)` | 1.4.4 实测签名：`CIMOptimizer(task_name, wait=False, interval=6, project_no=None, task_mode='optimization', sample_number=10)` | 按旧版传参会 TypeError | 官方 changelog；模块手册；`inspect.signature` 实测 |
| 8 | `interval` 单位 | 分钟（旧版） | **秒**，默认 6，下限 5；旧值需 ×60 | 轮询频率差 60 倍 | 官方 changelog v1.4.4 |
| 9 | 任务唯一标识 | v1.3：`task_name_prefix + MD5(ising_matrix)` | 1.4.4 `task_name` 仍为必传；任务由矩阵 + 任务名共同决定，重复提交同矩阵需换名 | 影响结果查询与缓存 | 官方 changelog；模块手册 |
| 10 | license 触发范围 | FAQ："首次使用 `CIMOptimizer`/`SimulatedAnnealingOptimizer` 时输入 user_id 和 sdk_code" | 实测：`SAOptimizer` 需要；`CIMOptimizer` 需要；**`BruteForceOptimizer`、`TabuSearchOptimizer`、`SimulatedAnnealingSampler` 不需要** | 无账号也能做本地建模与基线求解 | 旧 FAQ；本机实测 |
| 11 | 8bit 精度限制 | Ising 系数 `[-128,127]` | 未变；限制针对 **Ising 矩阵**，不是 QUBO 矩阵 | 建模后必须做精度适配 | 官方"参数精度"页 |
| 12 | QUBO→Ising 加变量 | 自动多 1 个比特（辅助变量） | 未变；实测 3 变量 → 4×4 Ising | 配额估算要多留 1 bit | 官方文档；实测 |
| 13 | Ising 能量符号 | 文档定义 `H = -ΣJijσiσj - μΣhiσi` | 未变；实测 `kw.common.hamiltonian` 返回 `-sᵀJs` | 自己写校验代码时符号必须对齐 | 官方概述页；实测 |
| 14 | SA 采样器行为 | 旧版多条链可能共享状态 | 1.4.4：各链独立运行、返回退火结束状态、保留重复样本 | 采样结果统计口径变化 | 官方 changelog v1.4.4 |
| 15 | 版本属性 | 惯用 `kw.__version__` | 实测返回 **1.0.8**（来自 `kaiwu-community`），不是 1.4.4；应使用 `importlib.metadata.version("kaiwu")` | 版本判断会误判 | 实测 |
| 16 | 官方 AI Coding Skill | — | 文档站导航、Changelog、FAQ 中均未发现官方 AI Coding Skill / MCP 说明 | 不作为依赖项，标记 UNVERIFIED | 文档站全站导航 + 检索 |
| 17 | 竞赛指定 SDK 版本 | — | 竞赛页需登录，未获取 | 影响最终提交环境一致性 | **BLOCKED** |

补充：官方 Changelog 中 1.4.2 标注"版本废弃，顺延到 1.4.3"，因此**不要安装 1.4.2**。

---

## 5. 已弃用 / 易踩坑 API 清单（按 1.4.4 实测）

| 旧写法 | 现状 | 正确写法（实测可用） |
|---|---|---|
| `kw.solver.SimpleSolver(opt)` | 模块不存在 | `opt.solve_qubo(qubo_model)` |
| `kw.qubo.QuboModel` / `kw.ising.*` | 模块不存在 | `kw.core.QuboModel`、`kw.core.ndarray`、`kw.core.get_sol_dict` |
| `kw.classical.SimulatedAnnealingOptimizer(...)` 直接跑 | 会弹 license 输入 | 先 `kw.license.init(user_id, sdk_code)`；或改用 `TabuSearchOptimizer` |
| `BruteForceOptimizer(size_limit=...)` | 不接受参数 | `BruteForceOptimizer()` |
| `kw.Binary(["x1","x2"])` | 只接受单个名字字符串 | `kw.core.ndarray((m,n), "x", kw.core.Binary)` 或逐个 `kw.core.Binary("x0")` |
| `get_sol_dict(solution, model)` | 需要变量字典 | `kw.core.get_sol_dict(sol, ising_model.get_variables())` |
| `kw.common.hamiltonian(mat, single_vector)` | 只接受二维解矩阵 | `kw.common.hamiltonian(mat, np.atleast_2d(sol))` |
| `calculate_ising_matrix_bit_width(...)` 当 int 用 | 返回 dict | 取 `result["precision"]`、`result["multiplier"]` |
| `SimulatedAnnealingSampler.run(...)` | 无 `run` 方法 | `.solve(matrix)` |

---

## 6. 对 D 题预研的影响

1. **工具链可用性**：建模、QUBO/Ising 互转、精度适配、本地求解均可在无账号条件下完成，技术门槛低于预期。
2. **真机门槛**：真机与官方 SA 优化器都被 license 卡住，且 license 与账号绑定。比赛中若队长账号未提前准备，会直接卡在 Phase 5。
3. **版本一致性**：由于"竞赛指定 SDK 版本"未知，提交前必须以竞赛页/官方通知为准；本仓库锁定 1.4.4 只是为了本地可复现，不代表赛事要求。
4. **文档可信度**：官方文档站（latest）与 FAQ 存在明显代际差异，**以模块手册签名和实际运行为准**。

---

## 7. 来源清单（访问时间均为 2026-11-26）

| 编号 | 来源 | 用途 |
|---|---|---|
| S1 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/> | 文档站首页与目录 |
| S2 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/getting_started/sdk_installation_instructions.html> | 安装说明 |
| S3 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/about/changelog.html> | 版本与 API 变更 |
| S4 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/getting_started/introduction.html> | 模块划分、Ising 定义 |
| S5 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/modules/kaiwu.cim.html> | CIMOptimizer 签名 |
| S6 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/precision.html> | 8bit 精度 |
| S7 | <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/mode.html> | Optimization/Sampling 模式 |
| S8 | <https://kaiwu.qboson.com/docs/FAQ.html> | 旧版 FAQ（对照用） |
| S9 | <https://pypi.org/pypi/kaiwu/json> | 版本、依赖、wheel 列表 |
| S10 | <https://cloud.qboson.com/> | 真机型号与公开定价 |
| S11 | <https://apmcm.org/uploads/files/20261020/1792484391858628.pdf> | 竞赛规则与时间 |
| L1 | 本机 `logs/phase1_pip_install.log` | 安装实测 |
| L2 | 本机 `logs/phase1_verify_env.log` | 环境自检实测 |
| L3 | 本机 `logs/phase1_license_state.log` | license 状态实测 |
