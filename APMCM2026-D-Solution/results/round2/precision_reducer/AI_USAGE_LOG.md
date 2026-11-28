# T003 AI 使用记录

- 时间：2026-11-28（Asia/Shanghai）
- 分支：`research/precision-reducer`（起点 `c001b08`）
- 环境：`kaiwu-original`（Python 3.12.5，Kaiwu 1.4.4）

## Trae（DeepSeek-V4.1-Flash）

- T003-01：用 `inspect`、`__doc__`、DEBUG 日志与最小调用核验本机 PrecisionReducer：
  构造/`solve` 签名、扩展矩阵捕获、`precision` 位宽语义、`target_bits` 上限、
  `only_feasible_solution` 行为、内部映射不公开。
- T003-02：实现非赛题教学闭环（无拆分、极端系数、one-hot 小案例）；小案例用
  `BruteForceOptimizer` 枚举 2^17 扩展空间，恢复后得到原始最优。
- T003-03：新增 `code/precision_reducer.py`；在 `d_experiment.py` 接入
  `precision_reducer` 路线（记录型组件、扩展矩阵、恢复、归档、resume）；
  扩展 `experiment_archive.py`（原始/扩展/提交矩阵、拆分映射、扩展解、可行解、恢复状态）。
- T003-04：新增 4 项回归测试；全套 32/32 通过；direct8 已知哈希不变；
  mock 端到端在临时实验根完成。
- T003-05：本地 G1–G4 对照（SA，5 seeds）；生成 `LOCAL_VALIDATION.json`、
  `G1_G4_LOCAL.json`；结论：拆分机制正确，但拆分一致样本率低，G3/G4 本地弱于 G1/G2。
- 未训练模型、未修改基线 B、未提交真机、未消耗量子配额。

## Codex（gpt-6.2-astra / xhigh / read-only）

- 调用 1 次；输入为 `%TEMP%\t003_codex_input` 中的 `MATH_VALIDATION.md`、
  `SDK_INTERFACE.md`、`LOCAL_VALIDATION.json`、`precision_reducer.py`。
- 核验问题：可行子空间等价命题、罚项充分性、tp12 的 V=0 来源、截断非单调、
  映射重建的可区分性、结论边界。
- 输出：`EXPERIMENTS/CODEX_REVIEW_01.json`（status=REVISE）。
- Trae 已按反馈修正：
  - 可行子空间等价改为 `Pᵀsym(T)P−c·sym(I_b)` 非对角为零的充要条件；
  - 删除“构造态低于采样值证明全局最优一致”的表述；
  - 改为“seed 3 有一致 V=0”，不再归因“多来自不一致”；
  - 截断表增加 `H_b(La-Zr)−min` 与并列标签，区分严格丢失/并列保留；
  - 映射证据改为“候选分组复现”，不称唯一识别；
  - 结论限定为本对照/预算/seed。
- 本轮无新增需要第二次调用的实质矛盾。

## 配额与真机

- 队员授权“仅提交 tp14”后执行 1 次：task `t20261128-161915-b_q2_k8_lowm_pr_tp14-d4f6e0ff`，
  status=completed；10 返回、拆分一致 2/10、恢复合法 2/10、两者同时 1/10，
  严格有效原始最优命中 1/10（样本 0，La-Zr V=0，扩展能量 −206404 与构造最优一致）；
  平台 pkl 向量与归档逐元素一致。
- 配额消耗 1；账面已用 7 / 剩余 25（平台余额待核实）。tp12 未提交。
- 平台报告已由人工登录下载并归档：SPQC-550，硬件 1.5511 ms，
  平台任务 ID `d833dedb...`，PDF 中 10 条向量与归档 10/10 一致。
- T003-FINAL：严格统计修正为 2/10、2/10、1/10、1/10；resume 保护已完成状态；
  PR #5 作为离线工具合并；集成测试 40/40；集成 PR #7 已创建，未自动合并。
