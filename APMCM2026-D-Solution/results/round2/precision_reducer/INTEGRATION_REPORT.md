# T003-03：工程融合报告

## 1. 修改文件

| 文件 | 修改 |
|---|---|
| `code/precision_reducer.py`（新增） | 扩展矩阵捕获、公开 split 复现核验、`construct/restore`、可行性检查、变量表、记录型组件 |
| `code/d_experiment.py` | `precision_method` 路线分派；`build_problem` 返回原始/扩展维度与映射；执行时用 `RecordingComponent` 捕获实际矩阵/返回；PR 恢复与归档；`resume` 对 PR 用归档映射恢复；配置支持 `pr_params` |
| `code/experiment_archive.py` | `TaskArchive.create` 支持 `precision_meta` / `expanded_matrix` / 自定义 root；新增扩展解、扩展能量、可行解、恢复状态文件；`submitted_mapping` 记录 `n_ising_original` 与 `split_extra_spins` |
| `tests/test_precision_reducer_route.py`（新增） | 4 项回归 |
| `results/round2/precision_reducer/EXPERIMENTS/local_validation.py`（新增） | 本地验证与 G1–G4 |

## 2. 两条路线

- `direct_8bit`：默认；行为、哈希、归档和恢复路径不变。
- `precision_reducer`：
  1. 以未量化 `I` 调用 `PrecisionReducer`（不先做 8bit 截断）；
  2. 通过记录型组件捕获实际传入矩阵 `T` 与底层返回 `E`；
  3. 用公开 split 接口复现 `T` 并核验常数比例，得到 `split_indices`/分组；
  4. 提交矩阵为 `adjust_ising_matrix_precision(T,8)`；`target_bits=550` 时与 `T` 相同；
  5. 保存 PR 恢复的原始解、扩展解、可行解与恢复状态；
  6. 若映射无法核验，`build_problem` 返回 `unavailable`，`execute_task` 拒绝进入提交。

## 3. 归档结构（PR 任务）

```text
config.json                     # precision_method/precision_params/n_ising_original/split_extra_spins
input/ising_matrix_raw.npz      # 未量化 Ising (17×17)
input/ising_matrix_expanded.npz # PrecisionReducer 扩展矩阵 (62/121/…)
input/ising_matrix.csv          # 实际提交矩阵（8bit）
input/split_mapping.json        # 映射核验证据、split_indices、groups、逐变量副本表
input/submitted_mapping.json    # 扩展变量表、A/B、原始维度、split_extra_spins
raw/solutions_expanded.npz      # 底层求解器返回的扩展解
raw/solution_energy_expanded.csv# H=-sᵀTs（扩展矩阵）
raw/solutions.npz               # PrecisionReducer 恢复后的原始维度解
raw/solutions_feasible.npz      # 拆分一致且可恢复的行（若存在）
raw/restore_status.json         # 拆分一致数、恢复核对、矩阵一致性
```

## 4. 关键限制

- `split_indices` 不是 SDK 公开属性；本仓库用“公开 split 复现 + 维度/非零位置/常数比例”
  核验。无法核验即拒绝提交，不伪造映射。
- `PrecisionReducer` 对拆分不一致样本也会给出恢复向量；这些向量不能作为保真证据。
  评价必须使用 `solutions_feasible.npz` 或 `restore_status.json` 中的一致样本。
- `only_feasible_solution=True` 在无可行样本时可能返回 0 行，不抛异常。
- 扩展维度未做平台容量硬校验；候选使用 `target_bits=550` 与 62/121 自旋，低于
  SPQC-550 的常见容量，但正式提交前仍需平台侧确认。
- 未实现 PrecisionReducer 的动态范围压缩（mutate）与 item split 的正式对照；
  本轮只使用 `method="var"` 的变量拆分。

## 5. 结果摘要

- 工程链路已跑通（mock 端到端、归档、恢复、测试）。
- 本地数学与 SA 证据显示：拆分机制正确，但拆分一致样本极少（1–10/100），
  G3/G4 明显弱于 G1/G2。
- 队员授权后完成 1 次真机（tp14，121 自旋）：10 返回、2 拆分一致，其中 1 个为
  La-Zr（V=0），扩展能量 −206404 与构造最优一致；平台 pkl 与归档一致。
  该结果表明 SA 的失败率不能直接外推真机，但单任务不足以估计命中率。
