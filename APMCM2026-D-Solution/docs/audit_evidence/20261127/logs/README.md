# 日志缺失说明

- 审计脚本的原始控制台 stdout **没有保存为文件**。`SCIENTIFIC_AUDIT.md` 中的数值是当时运行的记录，本目录不补造日志。
- 可复现的数学接口已固定为 `tests/test_math_interfaces.py`；候选/批次统计可参考 `scripts/science_margins2.py`。
- `scripts/science_margins.py` 是失败版本（concat 后列名重复），保留是为了说明迭代过程。
- `scripts/` 中的脚本按原样复制；在当前修复分支上，Q3 相关部分可能因 `load_pool` 新增的重复 (A,B) 保护而中止——这是预期行为，不是回归。
