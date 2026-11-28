# T003-01：本机 Kaiwu 1.4.4 PrecisionReducer 实际接口

- 环境：`%LOCALAPPDATA%\kaiwu-original\Scripts\python.exe`（Python 3.12.5，Kaiwu 1.4.4，
  `kw.__version__` 为 1.0.8）
- 方法：`inspect.signature`、`__doc__`、公开属性、DEBUG 日志与最小实际调用；未反编译、
  未读取授权凭据、未调用 license 提交。
- 官方文档：<https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/precision.html>、
  <https://kaiwu-sdk-docs.qboson.com/zh/latest/source/modules/kaiwu.preprocess.html>

## 1. 构造与调用

```text
kw.preprocess.PrecisionReducer(component, precision=8, target_bits=None,
                               only_feasible_solution=False, truncated_precision=20)
solve(ising_matrix=None, negtail_flip=True, sort_solutions=False) -> np.ndarray
set_matrix(ising_matrix) / get_hamiltonian() / on_matrix_change() / solve_qubo(...)
```

- `component` 必须是 `kw.core.IsingSolver` 风格对象（例如 `SimulatedAnnealingOptimizer`、
  `CIMOptimizer`）。本机实测：`PrecisionReducer.solve` 每次只调用一次
  `component.solve(expanded_matrix)`。
- 返回值是**原始维度** `n_original` 的自旋矩阵；扩展维度不会出现在返回值里。
- 本机实例属性：`matrix`（原始矩阵）、`_component`、`precision`、`target_bits`、
  `only_feasible_solution`、`truncated_precision`、`_hamiltonian`。
  **没有公开的 split_indices / 分组 / 恢复映射属性。**

## 2. 参数含义（实测）

- `precision`：目标系数位宽。DEBUG 日志为
  `Matrix size after reducing precision: N, precision: 8`。
  官方文档写作“小数位数”，与本机实际行为不一致；以位宽为准。
- `truncated_precision`：split 前的截断位宽；与 `precision` 的差值越大，新增变量越多。
  本机 Q2 lowM 实测：`tp=10/12/14/16` 分别对应有效截断 9/11/13/15 位（公开 split 复现）。
- `target_bits`：扩展后自旋数上限。`target_bits=17` 且原始 17 维时报错
  `The original matrix size cannot be larger than the matrix size after reducing the precision`；
  `target_bits=550` 时 Q2 lowM 得到 121 或 62 个自旋（取决于 `truncated_precision`）。
- `only_feasible_solution=True`：只返回拆分一致样本；若没有，**可能返回 0 行**。
  本机多次实测未抛出官方文档所述 `KaiwuError`；不能假定它会抛异常。
- `negtail_flip`：对返回解做整体翻转规范化（末位自旋统一），不影响拆分一致性。

## 3. 扩展矩阵

- 通过包装 `component.solve` 可无损记录 PrecisionReducer 实际传入的矩阵与返回向量。
- Q2 lowM（`precision=8, target_bits=550, truncated_precision=12`）：
  原始 17 → 扩展 62；`tp=14` → 121；`tp=16` → 246；`tp=18` → 496。
- 扩展矩阵满足 `calculate_ising_matrix_bit_width(T, 8)["precision"] == 8`；
  `target_bits=550` 时 `multiplier=1`，提交矩阵与扩展矩阵逐元素相同。
- 内部拆分映射未公开。可用公开
  `perform_precision_adaption_split` / `restore_split_solution` /
  `construct_split_solution` 复现：
  对截断矩阵 `round(I/s)*s`（`s=max|I|/(2^(bits-1)-1)`）调用 split，
  当维度、非零位置与逐元素常数比例全部吻合时，接受该 `split_indices`。
  Q2 lowM 的 `tp=12` 复现比例最大偏差 `1.4e-14`。
  **证据强度**：这支持“该候选分组在容差内复现所观测的扩展矩阵”，但不唯一识别
  SDK 内部映射；组内副本可交换、图对称性可隐藏标签置换，不一致行的代表副本选择/
  平票规则也可能不同。归档中明确标注 `verified_reconstruction`，不写成“官方映射”。

## 4. 官方文档与本机实测差异

| 项目 | 官方文档 | 本机实测 |
|---|---|---|
| `precision` | 小数位数 | 系数位宽（DEBUG 日志与扩展维度均支持） |
| `only_feasible_solution=True` 且无可行解 | 抛 `KaiwuError` | 返回 0 行（未抛异常） |
| split 映射 | 未说明 | 无公开属性；只能复现核验 |
| 返回维度 | 原多项式解 | 原始维度（已恢复） |

## 5. 结论

- 本机 PrecisionReducer 可正常运行，支持 SA 与 BruteForce 组件；单次 `solve` 只触发
  一次底层求解调用，配额估算仍按 1 次任务。
- 扩展矩阵可记录、可核验；拆分映射不公开，但可通过公开 split 接口复现并用常数比例
  核验；无法核验时本仓库拒绝进入提交阶段。
- `only_feasible_solution=True` 的异常行为与文档不一致，不能把“未抛异常”当作可行。
