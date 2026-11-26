# AGENTS.md — 本仓库的工作约定（给后续 AI/协作者）

## 1. 仓库定位

本仓库是 APMCM 2026 D 题的**技术预研**仓库，不是赛题求解仓库。

允许：环境搭建、SDK 学习、通用教学案例、文档核查、实验日志。
禁止：D 题模型设计、算法方案、求解结果、论文正文、研究结论。

如果用户要求在本仓库里直接做正式赛题，先提示合规边界，由用户决定是否另建目录并自行完成核心工作。

## 2. 硬性约束

1. **不伪造结果**：任何"真机结果""求解结果"必须来自实际运行，并有日志。未运行就写 `BLOCKED`。
2. **不保存凭据**：`user_id`、`sdk_code`、密码、Token、验证码一律不写入文件、不打印到日志。若用户粘贴，提醒并建议删除。
3. **不消耗算力**：任何真机任务提交前必须得到用户明确授权（任务数、矩阵规模、预计消耗）。
4. **不改系统环境**：只用 `environment/.venv`，不升级/卸载系统 Python 或 Anaconda 包。
5. **状态标记**：`PASS / FAIL / BLOCKED / UNVERIFIED` 四选一，不把"理论上可行"写成 PASS。

## 3. 环境与命令

```powershell
# 环境自检
environment\.venv\Scripts\python.exe environment\verify_env.py

# Phase 2 教学案例（无需 license）
environment\.venv\Scripts\python.exe examples\qubo_teaching_cases.py

# Phase 3 求解器与精度工具（无需 license）
environment\.venv\Scripts\python.exe examples\classical_solver_check.py
```

SDK 版本判断用 `importlib.metadata.version("kaiwu")`，不要用 `kw.__version__`（它返回 `kaiwu-community` 的 1.0.8）。

## 4. 代码约定

- Python 3.12，风格遵循 PEP 8，中文注释。
- 新实验脚本放 `examples/`，一个文件一个主题；结果写 `experiments/results/*.json`；日志写 `logs/*.log`。
- 变量解码按**变量名**读取，不按数组位置（约束会自动插入松弛变量）。
- 能量校验统一使用 SDK 约定 `H = -sᵀJs`。
- 结果 JSON 必须包含：命令、时间、矩阵形状、耗时、结论。

## 5. 文档约定

- 每份报告开头必须有"结论 + 状态"。
- 引用外部资料必须写来源 URL 和访问时间。
- 修改结论时同步更新 `README.md` 的状态表，避免文档互相矛盾。

## 6. 交付前检查

- [ ] 两个 example 脚本退出码为 0
- [ ] `logs/` 有本次运行的日志
- [ ] `experiments/results/` 的 JSON 可被 `json.load` 解析
- [ ] 文档中没有凭据、没有伪造结果
- [ ] `README.md` 状态表与实际一致
