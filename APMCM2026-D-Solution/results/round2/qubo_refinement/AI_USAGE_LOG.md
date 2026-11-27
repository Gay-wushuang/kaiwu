# T002-A AI 使用记录

- 时间：2026-11-28（Asia/Shanghai）
- 分支：`research/qubo-refinement`
- 起始提交：`b4ed23f6cbaa233e70fba20eb369807bc7cf1a6d`
- 正式基线：B

## Trae（DeepSeek-V4.1-Flash）

- 阅读允许范围内的数学接口代码、T002 第一阶段证据与公开文献种子。
- 向 Codex 提供四个数学问题、现有公式/事实边界与参考文献种子。
- 独立复算 Codex 给出的 4 组教学例子与关键命题：33/33 PASS（`TEACHING_VALIDATION/`）。
- 核验 5 篇文献的 arXiv/DOI 元数据（`REFERENCES.md`）。
- 归档 `MATH_RESEARCH.md`、`REFERENCES.md`、`OPEN_QUESTIONS.md`、`DECISIONS.md`。
- 未训练模型、未修改基线 B 预测、未提交真机、未消耗量子配额。

## Codex（gpt-6.2-astra / xhigh / read-only）

- 调用 1 次；输入为 `%TEMP%\t002a_codex_input` 中的问题、上下文和文献种子，未扫描整个仓库。
- 输出四个方向的数学研究备忘录：罚项阈值、目标变换、替代编码、量化误差；含公式、推导、反例、3 个手算例、文献引用和待队员解决的问题。
- 输出经 Trae 独立复算；未发现需要追加第二次 Codex 的实质性数学矛盾，因此本轮只调用 1 次。
- 未修改任何文件、未提交真机、未消耗配额。
