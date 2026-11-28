# T002-A 参考文献（已核验条目）

- 核验日期：2026-11-28
- 说明：以下条目的 arXiv 摘要页/期刊元数据已由 Trae 实际读取；论文引用前仍请按目标期刊格式复核作者顺序、卷页与 DOI。未核验的条目未列入。

## 1. QUBO/Ising 建模范式与罚项

1. Andrew Lucas, **Ising formulations of many NP problems**, *Frontiers in Physics* 2, 5 (2014).
   - arXiv: [1302.5843](https://arxiv.org/abs/1302.5843)
   - DOI: [10.3389/fphy.2014.00005](https://doi.org/10.3389/fphy.2014.00005)
   - 用途：约束/罚项、one-hot、Ising 表述的经典来源。

2. Fred Glover, Gary Kochenberger, Yu Du, **A Tutorial on Formulating and Using QUBO Models**, arXiv:1811.11538 (2018; v6 2019).
   - arXiv: [1811.11538](https://arxiv.org/abs/1811.11538)
   - 用途：QUBO 建模、罚函数、约束的精确表示与数值例子。

## 2. Domain-wall 编码

3. Jesse Berwald, Nicholas Chancellor, Raouf Dridi, **Understanding domain-wall encoding theoretically and experimentally**, *Philosophical Transactions of the Royal Society A* 381: 20210410 (2022).
   - arXiv: [2108.12004](https://arxiv.org/abs/2108.12004)
   - DOI: [10.1098/rsta.2021.0410](https://doi.org/10.1098/rsta.2021.0410)
   - 用途：domain-wall 的变量数、约束结构、与 one-hot 的理论比较；给出“每离散变量至少 d−1 个二值变量”的一般性论证（在其假设下）。

4. Jie Chen, Tobias Stollenwerk, Nicholas Chancellor, **Performance of Domain-Wall Encoding for Quantum Annealing**, *IEEE Transactions on Quantum Engineering* 2, 3102714 (2021).
   - arXiv: [2102.12224](https://arxiv.org/abs/2102.12224)
   - DOI: [10.1109/TQE.2021.3094280](https://doi.org/10.1109/TQE.2021.3094280)
   - 用途：domain-wall 与 one-hot 的变量数/嵌入/实验性能对照。

## 3. 有限精度

5. Jemma Bennett, Adam Callison, Tom O'Leary, Mia West, Nicholas Chancellor, Viv Kendon, **Using copies to improve precision in continuous-time quantum computing**, *Quantum Science and Technology* 8, 035031 (2023).
   - arXiv: [2206.02545](https://arxiv.org/abs/2206.02545)
   - DOI: [10.1088/2058-9565/acdcb5](https://doi.org/10.1088/2058-9565/acdcb5)
   - 用途：有限精度/能量间隙对基态保持的影响、复制提高有效精度的思路；本文只借用其“精度—能隙—基态”问题背景，不把复制方案作为本分支方案。

## 引用边界

- 上述文献支持通用数学机制与编码背景；不直接支持本赛题的正式参数、具体最优解或科学结论。
- 文献中的性能结论依赖具体硬件/问题实例，不能直接移植为本赛题结论。
- 若论文需要引用 Kochenberger 等的 QUBO 综述或 CPAIOR/ICCS 的罚项实践文章，应在投稿前另行核对卷页/DOI；本文件只列已实际核验的 5 条。
