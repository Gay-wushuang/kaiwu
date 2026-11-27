# 审计证据归档（2026-11-27）

本目录保存 Phase 10 科学审计实际使用的临时脚本、输入哈希、环境信息与关键 PDF 摘录。
目的：让审计结论可追溯，同时明确哪些原始证据已缺失。

## 文件

| 文件 | 内容 |
|---|---|
| `MANIFEST.json` | 归档脚本清单、SHA256、缺失说明、git 分支/提交 |
| `INPUT_HASHES.json` | 数据、预测、模型、平台 PDF、论文/题面 PDF 的 SHA256 |
| `ENVIRONMENT.json` | 两套 Python 环境与关键包版本 |
| `scripts/` | 原样复制的 10 个临时审计脚本 |
| `logs/pdf_key_values.json` | 从平台 PDF 提取的任务级关键值（非全文） |
| `logs/README.md` | 原始控制台日志缺失说明 |

## 重要限制

1. **原始控制台输出未保存为文件**。`SCIENTIFIC_AUDIT.md` 中的数值是当时运行的记录；本目录不伪造日志。
2. `science_margins.py` 是失败版本（DataFrame 重复列），保留以说明迭代过程；成功版本为 `science_margins2.py`。
3. 部分脚本依赖修复前的 `load_pool` 行为；在当前修复分支上重跑 Q3 相关部分会因“重复 (A,B)”中止，这是预期的保护。
4. 未归档任何账号、密码、`sdk_code` 或 Token。

## 使用建议

- 复核 QUBO/Ising/ΔH：先看 `tests/test_math_interfaces.py`（已固定为回归测试），再参考 `science_math_check.py`。
- 复核候选与批次：参考 `science_margins2.py`；当前模型/池批次不一致告警由 `code/artifact_consistency.py` 提供。
- 复核平台记录：以 `results/vendor_reports/*.pdf` 原文为准；本目录只存摘录与哈希。
