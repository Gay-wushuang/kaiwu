# T003-04：回归测试记录

- 环境：`kaiwu-verify`（Kaiwu 1.4.4）
- 命令：`python -m unittest discover -s tests -p "test_*.py"`
- 结果：**32/32 OK**（原有 28 + 新增 4）。

## 1. direct_8bit 回归

| 检查 | 结果 |
|---|---|
| `B-Q2-NO2` topk=8 lowM 提交矩阵 SHA256 | `34f84ed6633373975e3211b6099b20313a26d3734fa3770dded0187767454b30`（与 V3 真机提交一致） |
| `n_ising` / `resol_adj` | 17 / 7.0（未变） |
| 旧 JSON 配置（无 `precision_method`） | 自动按 `direct_8bit` 解析 |
| 归档字段 | 新增字段为追加式；旧字段与路径不变 |
| `resume` | direct8 分支逻辑未改 |

## 2. 新增 PrecisionReducer 测试

`tests/test_precision_reducer_route.py`：

1. `test_direct8_route_hash_unchanged`：锁定 direct8 哈希。
2. `test_precision_reducer_expansion_and_mapping`：17→62、45 个拆分自旋、17 组、
   映射状态 `verified_reconstruction`、8bit 可表示、变量表末位为 aux。
3. `test_constructed_optimum_is_split_feasible_and_restores`：原始最优构造的扩展态
   拆分一致，`restore_split_solution` 返回原始自旋。
4. `test_archive_with_precision_meta`：临时目录归档包含
   `split_mapping.json`、`ising_matrix_expanded.npz`、`ising_matrix_raw.npz`、
   `submitted_mapping.json`；维度 62/17/45 正确。

## 3. mock 端到端

- 临时实验根（`APMCM_EXPERIMENT_ROOT`）复制输入与配置，使用 `backend="mock"` 提交
  `precision_reducer` 任务。
- 结果：`completed`；归档包含扩展解、恢复解、`restore_status.json`；
  `recorded_matrix_matches_archived=true`；`split_feasible_samples=0/10`（mock 随机解）。
- 未调用 license、未创建云端任务、配额 0。

## 4. 未覆盖

- 真机返回（需授权）。
- 平台 PDF 与硬件能量复算（需真机任务）。
- 大规模（>550 自旋）拆分；`target_bits=None` 的 Q2 tp20 扩展 571 自旋未进入正式路线。
