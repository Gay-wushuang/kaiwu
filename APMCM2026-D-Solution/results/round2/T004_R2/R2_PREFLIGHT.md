# T004-R2 前置核验

- 时间：2026-11-28
- 分支：`research/final-hardware-validation`（从 `origin/main` 创建，FF 到 `f07f27f`）
- PR #8：OPEN、CLEAN、MERGEABLE，head `f07f27f`；**未合并 main**
- 真机：**0 新增**；配额：**0**

## 1. 基线 B 与历史任务

| 检查 | 结果 | 来源 |
|---|---|---|
| 基线 B 四个预测文件 SHA256 与 `SHA256SUMS.txt` 一致 | 4/4 PASS | `T004_FINAL/EXPERIMENTS/ACCEPTANCE.json` |
| Q1 holdout 3,703 行，SHA256 `9395cb54…` | PASS | 同上 |
| 7 个已完成任务，`quota_counted=true` 7 个 | PASS | `experiments/registry.json` |
| 7 个提交矩阵哈希复算一致 | 7/7 PASS | 同上 |
| 7 个平台 PDF SHA256 与 `task.json` 一致 | 7/7 PASS | 同上 |
| direct8 已知哈希 `34f84ed6…` 不变 | PASS | 同上 |
| Q3 NO2 与 Q2 输入同矩阵（V̂ 最大差 0） | PASS | `q3_audit.json` |
| 无 license/.env，无跟踪的 pycache | PASS | 同上 |
| 集中验收 | **33/33 PASS** | `ACCEPTANCE_CONSOLE.txt` |
| 回归测试 | **50/50 OK** | `T004_FINAL/EXPERIMENTS/REGRESSION_TESTS.txt` |

## 2. 相对自旋解码

- 实现：`code/precision_reducer.py::logical_bits_from_spins`：
  `x_i=(s_i*s_aux+1)/2`；末位为原始辅助自旋。
- 入口已统一：`d_submit_cim.py`、`d_run_stats.py`、`run_all.py`、`local_sa_stats.py`、
  `d_precision_reducer.py`、`task_audit.py`、`q3_audit.py`、`candidate_local_evidence.py`。
- 测试：`tests/test_t004_relative_decoding.py` 10 项；全量 50/50。
- 结论：R2 新增任务必须使用该口径；PR 先恢复原始维度再解码。

## 3. SDK 环境

| 项 | 值 |
|---|---|
| Python | 3.12.5（`%LOCALAPPDATA%\kaiwu-original`） |
| kaiwu 发行包 | **1.4.4** |
| `kaiwu.__version__` 属性 | 1.0.8（属性自报值；以 pip 发行包 1.4.4 为准） |
| numpy / pandas | 2.4.4 / 2.2.3 |
| license | 未加载；dry-run 不调用 license |

## 4. 容量与精度

- 本轮最大候选：Q3 O3 PR tp14 **196 自旋**；小于既有 `target_bits=550` 设定。
- 8bit 可表示性检查在 `d_experiment.build_problem` 中执行；所有候选 dry-run 通过。
- PR 扩展：Q3 O3 196（+169）、Q3 FO2 183（+156）、G3 129（+112）、重复 PR 121（+104）。
- direct8：27 / 17 自旋。

## 5. PR 接口与构造态

| 候选 | 映射 | 构造态可行 | 构造 H | 提交哈希 |
|---|---|---|---:|---|
| G3 Q2 M0 PR tp14 | verified_reconstruction（17 组） | 是 | -225194 | `87b44036…` |
| Q3 O3 lowM PR tp14 | verified_reconstruction（27 组） | 是 | -347004 | `e1bdb504…` |
| Q3 FO2 lowM PR tp14 | verified_reconstruction（27 组） | 是 | -308634 | `90d72b2d…` |

## 6. 无法完成的前置项

1. **平台余额**：需要队员登录平台核对；本地账本 32/7/25 只是账面值。
2. **设备选择**：SDK 不支持指定机型，设备由平台调度；不能预先保证同设备。
3. **平台计费方式**：未登录核对；按既有 1 任务=1 配额记录。
4. **真机执行**：未获授权，未提交。

## 7. 结论

工程前置条件满足 dry-run 要求；实际提交前仍需队员确认平台余额、候选清单和授权。
