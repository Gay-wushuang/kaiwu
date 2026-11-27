# CHANGELOG.md — Phase 10 最终质量冲刺

- 日期：2026-11-27（Asia/Shanghai）
- 分支：`engineering/final-quality`（基于 `main` @ `a372327`）
- 范围：仅普通工程缺陷；未改模型、算法、参数、随机种子与科学结论
- 真机提交：0 次；配额消耗：0

---

## [Unreleased] engineering/final-quality

### Added

| 编号 | 内容 | 原因 | 是否影响既有行为 | 测试证据 |
|---|---|---|---|---|
| E1 | `unknown_failure` 状态：未知阶段失败按“已提交”保守计数 | 原实现默认 `submit_failed`，可能少计配额并放行重复提交 | 是（未知异常不再算未提交） | `test_unknown_failure_is_conservative` |
| E2 | `_prepare_backend` 封装：授权/构造失败记为 `submit_failed` | 原实现失败后留下 `created` 状态，阻塞同名重试 | 是（失败可重试，且记录 `prepare:*`） | `test_backend_prepare_failure_is_retryable` |
| E3 | `validate_spin_matrix`：校验二维、列数、±1 取值 | 防止 SDK 异常返回被静默解码 | 是（非法解中止或标记 `invalid_result`） | `test_invalid_solution_shape_rejected`、`test_validate_spin_matrix` |
| E4 | `backup_if_exists`：写入前备份旧输出 | 降低历史脚本重跑覆盖旧结果的风险 | 是（多出 `*.bak-时间戳` 文件） | `test_backup_if_exists_preserves_old_output` |
| E5 | `d_run_stats` 记录 `sample_number_param` 与 `returned_solutions` | 区分“请求的采样参数”和“平台实际返回解数” | 是（统计 JSON 新增字段；dry-run 返回结构新增字段） | `test_dry_run_separates_requested_and_returned_samples` |
| E6 | README 脚本数量 15 → 20 | 文档与实际不一致 | 否（仅文档） | `Get-ChildItem code -Filter *.py` 计数 20 |
| — | 测试从 9 项扩展到 16 项 | 覆盖新增修复 | 否 | `python -m unittest discover -s tests -v` |

### Changed（行为变化细节）

1. `d_experiment.py`
   - 未匹配到已知阶段的异常不再归为 `submit_failed`，改为 `unknown_failure`，`quota_counted=True`，并参与重复提交拦截。
   - 授权或 `CIMOptimizer` 构造失败统一写为 `submit_failed`，`quota_counted=False`，允许同名重试。
   - 返回解先校验再归档；非法解写入 `raw/solutions.npz` 并标记 `invalid_result`（计配额、拦截重复）。
   - 提交前新增参数校验：`--topk` 不得为负或超过标签数；`--samples` 必须在 10..2000。
2. `d_submit_cim.py`
   - 返回解校验失败时直接中止，不写结果文件。
   - 结果 CSV 写入前备份旧文件。
3. `d_run_stats.py`
   - 返回解校验失败时直接中止，不写统计/逐样本/图。
   - stats/samples/图写入前备份旧文件。
   - dry-run 与提交统计新增 `sample_number_param`、`returned_solutions`；`samples` 在提交统计中仍表示实际返回解数。
4. `experiment_archive.py`
   - 新增 `unknown_failure`、`invalid_result` 状态文本。
   - `save_solutions` 对非整数数组使用 `%.10g` 保存，避免 `%d` 截断。
   - 新增 `validate_spin_matrix`、`backup_if_exists`。
5. `README.md`
   - 脚本数量与目录说明更新。

### Not Changed（明确未改）

- Hamiltonian 排序方向与图注（A1）
- 模拟退火 ΔH 系数（A2）
- 辅助自旋位置截断/变量名解码方式（A3）
- 分辨率口径（A4）
- “金标准”术语（A5）
- 优化模式 `sample_number` 文案（A6）
- 任何代理模型、QUBO 构造、罚项、目标函数、随机种子
- 任何历史实验产物、`date/` 数据、论文内容

### Verification

- `python -m compileall -q code tests` → 退出码 0
- `python -m unittest discover -s tests -v` → 16/16 PASS
- `python code/verify_project.py` → kaiwu-verify: PASS 15 / FAIL 0；kaiwu-original: PASS 15 / FAIL 0 / WARN 0
- `python code/d_submit_cim.py` → 退出码 0（1.87 / 2.94 档）
- `python code/d_run_stats.py ... --dry-run` → 退出码 0，`[DRY-RUN]`
- Gate 2：27 个平台解向量 H 复算最大偏差 0.000；合法解数 2/7、1/10、1/10

详见 `CODE_AUDIT.md` 与 `QUALITY_TEST_REPORT.md`。
