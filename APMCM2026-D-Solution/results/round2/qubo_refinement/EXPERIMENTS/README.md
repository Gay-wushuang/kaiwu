# T002-A V2 合成基准：one-hot 与 domain-wall 的有限精度对照

- 性质：**非赛题合成验证**，不是正式第二轮实验；不修改基线 B、不使用第一轮真机数据作为输入。
- 日期：2026-11-28
- 代码：`synthetic_encoding_benchmark.py`
- 原始结果：`synthetic_benchmark_results.json`（200 个随机实例 × 2 种惩罚强度 × 2 种编码）
- 运行环境：`kaiwu-verify`（kaiwu 1.4.4），单次运行约 **1.3 s**
- 全空间穷举：one-hot 8 个逻辑变量（256 状态）、domain-wall 6 个逻辑变量（64 状态）；均再经 `to_ising` + `adjust_ising_matrix_precision(8)` + SDK 反算 QUBO 后穷举。

## 设计

- 标签数 `d=4`，两个离散变量（A/B）× 4 标签；`V` 为 `4×4` 随机成本，`V~U(0,5)`，seed `20261128`，200 个实例。
- 两种编码：
  - one-hot：每个变量 `d` 位，罚项 `M[(Σe−1)²]`；
  - domain-wall：每个变量 `d−1` 位，合法码为 `000,100,110,111`，罚项 `M[(1−t1)t2+(1−t2)t3]`。
- 两种惩罚强度（同一编码内相同 M）：
  - strong：`M=1.05*max V`；
  - weak：`M=0.5*min V`。
- 目标成本在合法码上逐标签与 `V` 一致（两种编码均验证 `legal_equal_V_all=true`）。
- 量化：`I=to_ising(Q)`，`adj=adjust_ising_matrix_precision(I,8)`，再用 `kw.core.ising_matrix_to_qubo_matrix(adj)` 反算逻辑 QUBO 能量。
- 两个穷举范围要分开：最优标签集合在 **16 个合法标签**内比较；约束有效性在**全部 256（one-hot）或 64（domain-wall）个逻辑状态**上比较。两者都是全空间穷举，不是局部搜索。

## 聚合结果（200 实例均值）

| 编码 / 惩罚 | 保留比例 | 量化最优中非原始最优数 | Spearman | 未量化约束有效 | 量化后约束有效 | 未量化间隙 | 量化间隙 |
|---|---:|---:|---:|---:|---:|---:|---:|
| one-hot / strong | 0.970 | 0.250 | 0.99344 | 100% | 100% | +4.653 | +138.02 |
| domain-wall / strong | 0.990 | 0.050 | 0.99893 | 100% | 100% | +2.454 | +329.02 |
| one-hot / weak | 0.970 | 0.105 | 0.99724 | 0% | 0.5% | −0.157 | −13.84 |
| domain-wall / weak | 0.990 | 0.045 | 0.99932 | 0% | 0% | −3.884 | −705.14 |

变量/矩阵成本：

| 编码 | 逻辑变量 | Ising 维度 | 辅助自旋 | QUBO 维度 |
|---|---:|---:|---:|---:|
| one-hot | 8 | 9 | 1 | 8 |
| domain-wall | 6 | 7 | 1 | 6 |

- 两种编码的合法成本逐标签相同（`legal_equal_V_all=true`）。
- 同实例/同惩罚下，两种编码的量化合法最优集合在 **65/400** 组（16.25%）中不同；说明编码会改变量化后的排序/并列，即使合法域实数成本相同。
- strong 下两种编码在本批 200/200 实例中 exact/quant 约束均有效；weak 下两种编码的 exact 有效数均为 0/200。weak 量化后：one-hot 为 1/200 有效（187 个负间隙、12 个零间隙），domain-wall 为 0/200 有效（全部负间隙）。零间隙表示合法与非法并列，不是“有效”。
- domain-wall 在本合成设置中保留了更高的原始最优比例、较少的非原始最优和更高的排序相关性；但这是 d=4、随机 V、两种 M 的合成结果，不能外推为“domain-wall 一定更优”。

## 反例：强 M 也不保证 domain-wall 全空间约束有效

取 `4×4` 的 `V`：`V[0,1]=V[2,1]=V[1,0]=V[1,2]=4`，其余为 1；`M=1.05*max V=4.2`。domain-wall 的合法最低能量为 **1.0**，但非法码 `(010,010)` 的能量为 **−2.6**，间隙 **−3.6**。

原因：非法 domain-wall 码的指示量 `e_r` 不再是非负 0/1 指示，正 `V` 的交叉项可以产生负贡献；仅按 `V` 的最大值设定 M 不足以保证合法码胜出。因此：

- one-hot 的“`M>max V` 保证每个合法解优于所有非法解”不能直接搬到 domain-wall；
- domain-wall 需要按其自身非法码的负贡献/罚项层级设定阈值；
- 本基准 strong 的 100% 只是这 200 个随机实例的经验结果，不是普遍定理。

证据：`counterexample_strong_domainwall.py` / `counterexample_strong_domainwall.json`。

## 与第一轮/正式实验的边界

- 第一轮真机的 11/48 合法返回是**采样/硬件返回合法率**，不是全空间约束有效性；本基准的“约束有效”是穷举全逻辑空间的最优合法 vs 最优非法，口径不同，不能直接比较。
- 本基准不使用 `B-Q2-NO2` 等正式输入，不是第二轮正式实验；第一轮真机数据未重算、未修改。
- 未实现 binary 编码的系统对照（一般 `V` 需要高阶/辅助位），也未使用 PrecisionReducer/动态范围压缩/变量拆分。
- 结论仅支持：在本合成设置下，合法域等价不保证量化后最优集合相同；strong M 在本批随机实例中保持全空间约束有效，但存在 domain-wall 反例；weak M 会失效；domain-wall 在该样本下目标保真指标更好，但不能外推。

## 冻结 B 输入 topk=8 的全空间对照

使用 `B-Q2-NO2`、`B-Q3-O3`、`B-Q3-FO2` 的 topk=8 子矩阵（不是第一轮 topk=13 配置），比较 one-hot 的 M0 / lowM 与 domain-wall 四档 M；全逻辑空间穷举。结果文件：`domain_wall_bq_multi_results.json`。

| 输入 | OH M0：保留/非原始/Spearman | OH lowM：保留/非原始/Spearman | DW 1.05：保留/非原始/Spearman | DW 8：保留/非原始/Spearman | 约束有效（exact/quant） |
|---|---|---|---|---|---|
| B-Q2-NO2 | 0.000 / 5 / 0.7778 | 1.000 / 0 / 0.9779 | 1.000 / 1 / 0.99975 | 0.000 / 2 / 0.99138 | 全部 true |
| B-Q3-O3 | 0.000 / 1 / 0.8513 | 0.667 / 2 / 0.9087 | 0.333 / 0 / 0.99339 | 0.333 / 3 / 0.96579 | 全部 true |
| B-Q3-FO2 | 0.000 / 4 / 0.8255 | 0.000 / 1 / 0.9437 | 0.000 / 2 / 0.99667 | 1.000 / 1 / 0.97991 | 全部 true |

- M0 为现有 `build_qubo` 默认罚项（第一轮 one-hot 实际使用）；lowM 为 `M=1.05*max V`（mfactor 见候选配置）。
- 规模：one-hot 16 逻辑变量 / Ising 17；domain-wall 14 / Ising 15；两者各 1 个辅助自旋。
- 在 B-Q2-NO2 上，lowM 将原始最优集合完整保留（非原始最优 0），而 M0 丢失原始最优；这是本轮唯一达到“集合相等”的候选。
- Q3 O3/FO2 没有跨 M 的集合相等；domain-wall 也没有稳定占优。不能从本对照直接选出通用编码。

## T002-A V4：one-hot 罚项尺度扫描与误差结构

- 脚本：`onehot_mfactor_scan.py`（14 个 `M/Vmax` × 3 输入，topk=8，全逻辑空间穷举）、
  `onehot_quant_error_structure.py`（合法 8×8 能量的量化误差分解）。
- 结果：`onehot_mfactor_scan_results.json`、`onehot_quant_error_structure.json`；
  数学结论与证据分级见 `../ONEHOT_STABILITY.md`。
- 集合相等只在 `B-Q2-NO2` 的 `M/Vmax=1.05`、`1.10` 两个**孤立点**出现；补算 1.075
  时 La-Zr 与 La-Hf 并列（−1728），不相等。2.80 时原始最优重新出现但多 1 个非原始最优，
  因此“≥1.40 均丢失”不成立。M0（3.10）丢失原始最优，与第一轮 0/5 原始命中一致。
- 量化后 `quant_gap>0`（基态合法）在 42/42 点成立；但 `quant_separation<0`
  （最佳非法优于最差合法）在低 M 点成立，例如 Q2 的 1.05 为 −4。两者必须分开报告。
- 误差结构：Q2 原始最优间隙仅 0.001396，而量化残差摆动约 3.5–3.9 个原单位；
  1.05/1.10 的“集合保持”来自 4 个整数单位的人造裕量，1.075 即被破坏。
- 代码口径修正：目标块用 `np.array_equal` 严格比较；`diff_count` 明确为矩阵位置数并另报
  独立边数；辅助位不参与合法性判定，量化能量取其最小可达值。



第一轮真机：48 返回 / 11 合法（采样合法率）、量化合法最优命中 5/5、返回合法解命中原始最优 0/5。本基准是合成成本表上的全空间枚举：`quant_valid_rate` 是“最优合法 vs 最优非法”的全空间约束有效性，不是硬件采样合法率；“保留比例/非原始最优”是 16 个合法标签集合指标。两者口径不同，**不能计算或声称相对第一轮的指标升降**。第一轮数据未重算、未修改。

## 是否具备下一轮真机条件

已实施 1 次：`B_Q2_k8_lowM`（B-Q2-NO2，topk=8，one-hot，`mfactor=0.33826009024559534`，M=14.265，Ising 17）。本地全空间：原始最优保留 1.0、非原始最优 0、Spearman 0.9779、exact/quant 约束有效、分辨率 7.10/7.00 档；第一轮同输入 M0（分辨率 3 档）本地保留 0.0。真机返回 La-Zr（H=−1716，V=0），原始/量化命中 1/1，合法 2/10；设备 SPQC-1，硬件 4.3098 ms。详见 `REAL_MACHINE_CANDIDATES/RESULTS.md`。当前真机已用 1 次，剩余 26。

## 复现

```powershell
& "$env:LOCALAPPDATA\kaiwu-verify\Scripts\python.exe" `
  results/round2/qubo_refinement/EXPERIMENTS/synthetic_encoding_benchmark.py
& "$env:LOCALAPPDATA\kaiwu-verify\Scripts\python.exe" `
  results/round2/qubo_refinement/EXPERIMENTS/domain_wall_bq_multi.py
```

输出 `synthetic_benchmark_results.json`（800 条逐实例记录）与 `domain_wall_bq_multi_results.json`（3 个 B 输入、topk=8）。Codex 核验记录见 `CODEX_REVIEW_01.json`。
