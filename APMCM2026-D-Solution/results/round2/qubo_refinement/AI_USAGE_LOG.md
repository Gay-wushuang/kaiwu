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
- 追加 one-hot 罚项缩放检查：B-Q2-NO2 topk=8 的 M0=42.171 本地保留 0.0、非原始 5、分辨率 3；`lowM=1.05*max V`（mfactor 0.33826009024559534，M=14.265）本地保留 1.0、非原始 0、分辨率 7.10/7.00、量化约束有效。已生成 `REAL_MACHINE_CANDIDATES/B_Q2_k8_lowM.json` 并执行 `d_experiment plan` dry-run（未调用 license、未提交、配额 0）；等待真机授权。
- 队员授权后提交 `B_Q2_k8_lowM` 1 次：task `t20261128-043036-b_q2_k8_lowm-34f84ed6`，状态 completed；返回 10、合法 2，最低合法 La-Zr（H=−1716，V=0），原始/量化最优命中 1/1；设备 SPQC-1，硬件 4.3098 ms，端到端 7.754 s。平台 PDF 已归档；配额已用 6、剩余 26。未重复提交。

## T002-A V4：one-hot 数学表达深化与有限精度稳定性

- Trae（DeepSeek-V4.1-Flash）：
  - 实现并运行 `EXPERIMENTS/onehot_mfactor_scan.py`（3 输入 × 14 个 `M/Vmax`，共 42 点；
    topk=8，全逻辑空间穷举），增加 1.075 点，区分 `legal_set_equal`、
    `quant_fullspace_valid`、`quant_gap`、`quant_separation`。
  - 实现并运行 `EXPERIMENTS/onehot_quant_error_structure.py`（合法 8×8 量化能量、
    有效尺度 α、残差两向分解、逐点翻转量），生成 `onehot_quant_error_structure.json`。
  - 修正 `lowm_coeff_delta.py` 的目标块比较为 `np.array_equal`，明确 `diff_count` 与
    独立边数、舍入误差单位；修正合法能量对辅助位取最小值的口径。
  - 在 `code/d_experiment.py` 增加 `adapt_precision` 分派与 `precision_method` 标识
    （默认 `direct_8bit`），不改变现有矩阵与哈希；23 项实验管线测试与 5 项数学接口测试通过。
  - 撰写 `ONEHOT_STABILITY.md`；未选择正式方案、未提交真机、配额消耗 0。
- Codex（`gpt-6.2-astra` / `xhigh` / `read-only`）：调用 1 次，输入
  `EXPERIMENTS/CODEX_REVIEW_02_QUESTION.md` 与同目录数据；输出
  `EXPERIMENTS/CODEX_REVIEW_02.json`（REVISE）。Codex 独立复算 39 点，补算 1.075
  并发现 La-Zr/La-Hf 并列，指出 2.80 反例、`np.allclose(atol=0)` 的默认相对容差、
  集合相等的两种口径，并给出带符号误差判据与 `Δ>2ε` 充分条件。Trae 已按反馈修正；
  本轮无新增需要第二次调用的实质数学矛盾。
- 本轮真机 0 次、配额 0；账面剩余 26，平台余额待核实。

