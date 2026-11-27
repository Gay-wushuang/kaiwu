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

## T002-A V2：合成编码基准

- Trae：实现 `EXPERIMENTS/synthetic_encoding_benchmark.py`，对 200 个非赛题随机 4×4 成本表比较 one-hot 与 domain-wall、strong/weak 两档 M；全逻辑空间穷举（one-hot 256 状态、domain-wall 64 状态）；运行约 1.2 s；生成 `synthetic_benchmark_results.json` 与 `EXPERIMENTS/README.md`。未使用赛题输入、未修改第一轮数据、未提交真机、配额 0。
- Codex（`gpt-6.2-astra` / `xhigh` / `read-only`）调用 1 次；返回 REVISE，指出 Spearman 常量秩应记为未定义、README 的 weak 有效数需精确、strong 100% 不是普遍保证，并给出 domain-wall 强罚项反例。Trae 修正 Spearman（`null` + 有效条数），补录 weak 计数，并新增反例脚本/JSON；独立复现反例：M=4.2 时合法最低 1.0、非法 (010,010) 为 −2.6。
- 本次没有新增需要第二次 Codex 的未解决矛盾；Codex 调用合计 1 次（V2）。
- 追加冻结 B 输入 topk=8 全空间对照（`B-Q2-NO2`、`B-Q3-O3`、`B-Q3-FO2`）：one-hot 与 domain-wall 无跨输入稳定占优；Q2 one-hot 保留 1.0，O3 0.667，FO2 0.0；domain-wall 分别为 1.0（含额外非原始最优）、0.333、部分 M 下 1.0。未产生可提交真机的候选，未消耗配额。

