# T004-R1 数学核验纠偏报告

- 分支：`research/final-validation`
- 起点：`31d7de86c9d62600682193f808842345f29063ab`
- 真机新增：**0**；配额消耗：**0**
- 历史提交矩阵、预测结果、平台 PDF、原始返回向量：**未修改**

## 1. 错误总览

| 编号 | 错误 | 旧口径 | 新口径 | 影响 |
|---|---|---|---|---|
| E1 | 直接用物理自旋判定 one-hot | `x_i=(s_i+1)/2` | `x_i=(s_i*s_aux+1)/2` | 全局翻转被误判为非法逻辑态 |
| E2 | 同一物理 `s` 单独切换 aux 取最小能量 | `min(H(s,+1), H(s,-1))` | 固定 `aux=+1` 规范代表枚举逻辑状态 | 产生虚假的“全空间非法最低 = 合法最低” |
| E3 | 声称“全局翻转产生非法互补态，全空间基态必含非法态” | 物理位判定 | 全局翻转是同一逻辑状态，合法性不变 | 结论反转为“全空间逻辑基态全部合法” |
| E4 | 声称“量化集合排除原始最优 ⇒ 合法样本不可能命中” | 量化基态 = 采样集合 | 量化基态 ≠ 启发式返回集合 | G1 本地 SA 5/5 是反例 |
| E5 | 声称“任一原始最优必被 topk 保留” | 无条件的行/列最小值论证 | 仅在实际映射上逐一核对；并列截断有反例 | Q3 6/6 保留是数据结果，不是定理 |
| E6 | PR 本地 tp14 命中记成 1/5 | tp12 与 tp14 混写 | tp12 1/5；tp14 0/5 | T003 KEY_COMPARISON 已修订 |

## 2. E1/E2/E3：辅助自旋与相对自旋解码

### 2.1 原因

含辅助自旋的 Ising 模型里，逻辑变量应按相对自旋定义：

\[
x_i=\frac{s_i s_{\rm aux}+1}{2}.
\]

旧代码把 `s_i` 直接当逻辑位，并且在 `legal_energies` / `exact_submitted_space` /
`task_audit` 中对同一个物理 `s` 分别取 `aux=+1` 和 `aux=-1` 的较小能量。后者会把
`(s, aux=+1)` 与 `(s, aux=-1)` 当成同一逻辑候选的两个规范，但实际它们是**不同逻辑状态**
（除非同时翻转全部自旋）。正确做法：固定 `aux=+1` 规范代表，`s` 与 `-s` 是同一逻辑状态的两个
物理代表，能量相同。

### 2.2 修正位置

- `code/precision_reducer.py`：新增 `logical_bits_from_spins`、`logical_labels_from_spins`；
  `evaluate_restored` 改用相对自旋。
- `code/d_submit_cim.py`、`d_run_stats.py`、`run_all.py`、`local_sa_stats.py`：
  采样解码改为相对自旋。
- `code/d_precision_reducer.py`：恢复后合法性检查改为相对自旋。
- `EXPERIMENTS/q3_audit.py`：`legal_energies` 固定 aux=+1；`exact_submitted_space` 只枚举
  规范代表；硬件解码改为相对自旋。
- `EXPERIMENTS/task_audit.py`：`decode_rows` 与量化合法集合改为相对自旋。
- `EXPERIMENTS/candidate_local_evidence.py`：合法域枚举固定 aux=+1。
- `EXPERIMENTS/space_gap_audit.py`：输出改为逻辑间隙。

### 2.3 复算结果

direct8 实例全空间逻辑枚举（2^26 / 2^16）：

| 任务 | 合法最低 H | 非法最低 H（逻辑） | 间隙 | 全部逻辑基态合法 |
|---|---:|---:|---:|---|
| B_Q2_baseline | -3018 | -2982 | 36 | 是 |
| B_Q2_m3x | -3120 | -3084 | 36 | 是 |
| B_Q2_k8 | -1780 | -1716 | 64 | 是 |
| B_Q3_O3 | -2962 | -2938 | 24 | 是 |
| B_Q3_FO2 | -2912 | -2876 | 36 | 是 |
| B_Q2_k8_lowM | -1716 | -1656 | 60 | 是 |

- 5 个已独立审查任务的合法最优集合大小不变：O3 3、NO2 5、FO2 7、Q2 k8 5、lowM 1。
- Q2 m3x 新增核验：合法最低 -3120，非法 -3084，间隙 36。
- 旧记录 `gap_anyaux=0` / `min_illegal_anyaux=min_legal` **删除**；它来自把合法态的全局翻转
  误当成非法逻辑态。
- 旧记录 `gap_aux_plus` 的数值 24/36/36/64/36/60 保留，并改名为 `gap_logical`。

### 2.4 结论修正

- 旧：“全空间基态必然同时含合法与非法互补态；全空间基态全部合法不成立。”
- 新：“全局翻转保持逻辑 `x` 与 one-hot 合法性；27 自旋 direct8 实例的全空间**逻辑**基态全部合法，
  合法-非法间隙 24–64 个 H 单位。”
- 不得把 27 自旋结论外推到 PrecisionReducer 的 121 自旋扩展空间。

## 3. E4：量化基态与采样命中

### 3.1 原因

量化模型 `B` 的合法基态集合、精确求解器返回集合、启发式/硬件采样集合是三个不同对象。
原始最优不在 `B` 中，只能说明“精确返回量化基态不能保证原始最优”，不能排除启发式返回非基态。

### 3.2 证据

- G1（M0 direct8, topk8）的量化合法最优集合为 BaTa、CaTa、LaTa、LaTi、PbTa，不含 LaZrO2N。
- 但 `G1_G4_LOCAL.json` 显示 G1 本地 SA 5/5 个种子都返回了 LaZrO2N 合法解（非基态采样）。
- G1 真机 0/10 是本次观测，不是不可能性证明。

### 3.3 修正位置

- `Q3_EVIDENCE.md` 第 7、10 节。
- `CONTROLLED_COMPARISON.md` 第 4、6 节。
- `REAL_MACHINE_CANDIDATES/SUBMISSION_LIST.md`。
- `PAPER_CHANGE_LIST.md` 第 4 节。

## 4. E5：Top-K 并列截断

### 4.1 原因

`select_topk` 按行最小值、列最小值分别 `argsort` 取前 K。全局最优 (a*,b*) 的行、列最小值都等于
全局最小值，但当并列值跨越截断边界时，`argsort` 的具体顺序可能把 a* 或 b* 切掉。

### 4.2 反例

\[
V=\begin{pmatrix}1&1&0\\0&1&1\\1&0&1\end{pmatrix},\quad K=1.
\]

行、列最小值都为 0；topk=1 选第 0 行、第 0 列，子矩阵为 `[[1]]`，原始最优 (0,2)、(1,0)、(2,1)
全部丢失。测试：`tests/test_t004_relative_decoding.py::TopKTieBoundaryTest`。

### 4.3 正式 Q3 的实际核对

基线 B 的 Q3 共 6 个原始最优；`q3_audit.json` 的 `topk_raw_hits` 分别为 3/1/2，
`topk_retains_all_raw_argmins=true`，即实际候选映射保留了全部 6 个。**这是数据核对结果，
不是无条件定理。**

## 5. E6：PrecisionReducer 本地统计

以原始 JSON 为准：

| 组 | 路线 | 严格原始最优命中 |
|---|---|---:|
| G1 | M0 + direct8 | 5/5 |
| G2 | lowM + direct8 | 5/5 |
| G3 | M0 + PR tp12 | 0/5 |
| G3 | M0 + PR tp14 | 0/5 |
| G4 | lowM + PR tp12 | 1/5 |
| G4 | lowM + PR tp14 | **0/5** |

- `1/5` 属于 **tp12**，不属于 tp14。
- 真机 tp14 严格有效原始最优仍为 **1/10**，未恢复为此前错误的 2/10。
- `results/round2/T003_FINAL/KEY_COMPARISON.md` 已加修订说明；原始 JSON 未删除、未重跑。

## 6. 数据变化与不变

### 6.1 发生变化

- `gap_anyaux=0` 与 `min_illegal_anyaux=min_legal` 删除；替换为 `gap_logical` 与
  `all_logical_ground_states_legal=true`。
- `submitted_space_exact` 字段名更新；旧 `aux_plus/anyaux` 字段不再输出。
- Q3 文档中“全空间基态必含非法态”的结论撤回。
- `KEY_COMPARISON.md` 的 tp14 本地命中从 1/5 更正为 0/5（并保留修订记录）。
- FINAL_METRICS 新增 `LOCAL_SA` 行与 `all_logical_ground_states_legal` 行。

### 6.2 保持不变

- 7 个真机任务的返回样本数、合法数、拆分一致数、严格命中数。
- Q2/Q3 原始最优集合与量化合法最优集合（数值与成员均未变）。
- direct8 提交矩阵哈希、基线 B 预测哈希、平台 PDF、原始返回向量。
- G1/G2/G3/G4 的本地种子命中数（除 tp14 的误记更正）。
- 真机 tp14 严格命中 1/10。

## 7. 独立核验

- 新增 `tests/test_t004_relative_decoding.py`：10 项，覆盖 aux=+1/aux=-1 解码、全局翻转逻辑不变、
  H 不变、合法/非法翻转、单独翻 aux、PR 恢复解码、Top-K 反例、量化基态/采样分离。
- 全量回归：**50/50 OK**（原 40 + 新增 10）。
- Codex：本轮按约定发起 **1 次** `gpt-6.2-astra / xhigh / read-only` 复核请求
  （`CODEX_REVIEW_T004R1_QUESTION.md`）。该次调用因账户 usage limit 未返回最终逐项意见。
  部分输出指出“本地 SA 汇总脚本仍有旧解码”，该问题已在 `d_run_stats.py`、`local_sa_stats.py`、
  `run_all.py` 中同步修复。日志未入库。因此本轮结论由本地精确枚举和 50 项测试支撑，
  **不冒充 Codex 已核验**。待额度恢复后，可用同一问题文件重试。

## 8. 仍未解决的数学问题

1. 121 自旋 PrecisionReducer 扩展空间的全空间逻辑枚举未做；不能声称“所有扩展基态拆分一致”。
2. Q3 6 个候选的真实物理 V=0 未验证。
3. 量化基态集合与启发式采样集合的包含关系没有一般定理；只能逐实例/逐样本报告。
4. Top-K 在并列截断下的保留性质没有通用保证；正式 Q3 的 6/6 是实例数据。
5. SDK/平台是否固定 aux=+1 未证明；只能记录“返回样本 aux 均为 +1”。
