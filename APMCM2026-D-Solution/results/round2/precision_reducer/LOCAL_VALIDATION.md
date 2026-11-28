# T003-02/03：PrecisionReducer 本地最小闭环与工程验证

- 非真机、非 license；组件使用 `SimulatedAnnealingOptimizer` / `BruteForceOptimizer`。
- 原始数据：`EXPERIMENTS/LOCAL_VALIDATION.json`、`EXPERIMENTS/G1_G4_LOCAL.json`。
- 工程入口：`code/precision_reducer.py`、`code/d_experiment.py`、`code/experiment_archive.py`。

## 1. 最小闭环（教学矩阵）

| 案例 | 原始维度 | 扩展维度 | 结果 |
|---|---:|---:|---|
| 无拆分（m1，5×5） | 5 | 5 | 返回原始维度解 |
| 极端系数（m2，含 10000） | 5 | 163 | 返回原始维度解；SA 样本需拆分一致才可恢复 |
| 小型 one-hot（d=2，V=[[0,0],[1,0.5]]） | 5 | 17 | **全空间枚举扩展问题**，恢复后最优集合 = 原始最优集合 |
| B-Q2-NO2 lowM | 17 | 62/121/246 | 映射重建通过；拆分一致样本率见下 |

小案例使用 `BruteForceOptimizer` 枚举扩展问题（2^17），恢复后的 4 个最优解均解码为
V=0（原始最优）。这验证了“拆分嵌入 + 恢复”在可穷举规模下保持原始最优集合。

## 2. 拆分映射重建（公开接口复现 + 常数比例核验）

| 输入 | `tp=10` | `tp=12` | `tp=14` | `tp=16` |
|---|---:|---:|---:|---:|
| B-Q2-NO2 | 36 / 9bit | 62 / 11bit | 121 / 13bit | 246 / 15bit |
| B-Q3-O3 | 36 / 9bit | 59 / 11bit | 123 / 13bit | 250 / 15bit |
| B-Q3-FO2 | 36 / 9bit | 55 / 11bit | 119 / 13bit | 235 / 15bit |

- 所有条目 `mapping_status=verified_reconstruction`：维度、非零位置、逐元素常数比例均吻合。
- Q2 `tp=12`：比例最大偏差 `1.4e-14`，`split_indices=[2,5,8,...,61]`，17 组。
- `precision=4` 的小案例未能在 8..20 位搜索到比例匹配，映射记为 `unavailable`；
  这不影响装饰器自身的解恢复，但本仓库的正式路线要求映射可核验。

## 3. 拆分一致性与可恢复性（每 100 个 SA 样本）

| 输入（tp=12） | 拆分一致 | 可恢复合法 | 可恢复最优 V | 全部返回合法 | 全部返回最优 V |
|---|---:|---:|---:|---:|---:|
| B-Q2-NO2 | 4–7 | 1–2 | 4.211 / 2.360 / 6.934 / **0.000** / 10.668 | 51–58 | 4.211 / 2.360 / 3.226 / **0.000** / 0.437 |
| B-Q3-O3 | 5–9 | 1–2 | 11.969 / 11.612 / 11.170 / 11.786 / 5.141 | 48–54 | 11.969 / **0.000** / 11.170 / 6.189 / 5.141 |
| B-Q3-FO2 | 5–10 | 1–3 | 0.027 / 0.130 / 0.008 / **0.000** / 0.478 | 45–62 | 0.027 / 0.039 / 0.008 / **0.000** / 0.478 |

要点：

- **“全部返回合法/最优”不等于拆分一致**。PrecisionReducer 会对拆分不一致的扩展解也
  做恢复；这些解可能解码为合法标签，但不对应任何拆分一致的扩展状态。
- 只有 `split_feasible + restore` 的行才是数学上有效的恢复证据；其数量只有 1–3/100。
- V=0 的来源不能一概而论：Q2 tp=12 的 seed 3 存在拆分一致的合法 V=0；其余 seed 的
  V=0 需逐行配对扩展样本与 SDK 恢复结果才能归因，现有汇总不足以判定。
- `tp=14/16` 的拆分一致率降到 1/100；`tp=10` 较高（约 50–65/100），但有效截断只有 9 位。

## 4. 构造最优解的可行性（Q2 lowM）

把原始最优自旋（La-Zr + aux=+1）用 `construct_split_solution` 嵌入扩展空间：

- 对 `tp=10/12/14/16` 全部拆分一致（`constructed_feasible=true`）。
- `tp=12` 时，构造解能量在 seed 0/1/2/4 低于 SA 100 样本的最小值（差 284、164、476、720），
  在 seed 3 与最小值持平（差 0），且 seed 3 恰有 1 个拆分一致的合法 V=0 样本。
  准确表述是“4 个 seed 未搜到、1 个 seed 持平”，不是“从未搜到”。
- 构造态低于采样最小值**不能证明**扩展全局最优一致；它只是 `E_C` 的上界证据，
  没有给出不一致子空间下界 `E_U`。
- `tp=12` 的有效截断为 11 位，原始 0.001396 的间隙在截断矩阵中已被改变（见
  `MATH_VALIDATION.md`）；因此构造解的“原始 V=0”不一定是截断问题的全局最优。

## 5. G1–G4 本地对照（SA，5 seeds，每 seed 100 样本）

| 组 | 路线 | Q2：合法数 / 原始命中 seed | O3：合法数 / 命中 | FO2：合法数 / 命中 |
|---|---|---|---|---|
| G1 | M0 + direct8 | 70–76 / 5/5 | 70–74 / 5/5 | 68–78 / 5/5 |
| G2 | lowM + direct8 | 72–77 / 5/5 | 68–88 / 5/5 | 68–74 / 5/5 |
| G3 | M0 + PR（tp12） | 全部返回合法约 51–58 / 0/5；一致最优 V 6.57–10.56 | 约 48–54 / 0/5；一致最优 V 0.21–13.92 | 约 45–62 / 0/5；一致最优 V 1.41–12.56 |
| G4 | lowM + PR（tp12） | 约 51–58 / 1/5；一致最优 V 0–10.67 | 约 48–54 / 0/5；一致最优 V 5.14–11.97 | 约 45–62 / 1/5；一致最优 V 0–0.478 |

- 本表来自 `G1_G4_LOCAL.json`（SA 1000 初温、100 iter/T、100 样本、5 seeds）。
- G1/G2 的 direct8 在相同 SA 预算下 5/5 命中原始最优；G3/G4 的 PrecisionReducer
  在拆分一致子空间内只有 1–3 个候选/100 样本，最优 V 明显更差。
- 该结果只支持“**本对照、本预算、本后端**下 direct8 更优”，不能否定 PR 在其他参数、
  预算、后端或实例上的可能性（Codex 核验意见）。
- 是否值得用真机配额验证硬件行为，由队员决定。

## 6. 工程闭环

- `d_experiment.py` 新增 `precision_reducer` 路线；`build_problem` 返回原始/扩展维度、
  `split_indices`、分组、映射状态、扩展矩阵哈希。
- `execute_task` 用 `RecordingComponent` 捕获底层实际矩阵与返回；归档：
  - `input/ising_matrix_raw.npz`（未量化 Ising）
  - `input/ising_matrix_expanded.npz`（PrecisionReducer 扩展矩阵）
  - `input/ising_matrix.csv`（实际提交矩阵）
  - `input/split_mapping.json`（重建证据 + 62/121 变量表）
  - `raw/solutions_expanded.npz`、`raw/solution_energy_expanded.csv`
  - `raw/solutions.npz`（PrecisionReducer 恢复后的原始维度解）
  - `raw/solutions_feasible.npz`（仅拆分一致且可恢复的行，若存在）
  - `raw/restore_status.json`（拆分一致数、恢复核对数、矩阵一致性）
- `resume` 对 PR 任务用归档的 `split_mapping.json` 恢复；映射缺失时拒绝恢复原始变量。
- mock 后端端到端测试：临时实验根下完成创建、求解、归档、恢复检查；
  `recorded_matrix_matches_archived=true`。
