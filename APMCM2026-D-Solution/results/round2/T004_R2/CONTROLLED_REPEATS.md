# T004-R2 同设备受控与重复实验

- 本轮新增重复：**0**
- 状态：仅准备候选与规则，未提交

## 1. 设备可控性

- `d_experiment.py` 明确不提供设备选择参数；SDK 不支持指定机型，设备由平台调度。
- 已有设备：G1 `B_Q2_k8` SPQC-550；G2 `B_Q2_k8_lowM` SPQC-1；
  G4 `B_Q2_k8_lowM_PR_tp14` SPQC-550。
- 因此现有 G1/G2/G4 不是同设备单因素对照；即使 R2 重复，也只能在实际分配设备后
  标注“是否恰好同设备”，不能预先声称控制设备。

## 2. 可形成的比较（若队员授权并恰好同设备）

| 比较 | 只改变 | 对照对象 | 需要的候选 |
|---|---|---|---|
| G1 vs G2 | 罚项 M（M0 vs lowM） | `B_Q2_k8` vs `B_Q2_k8_lowM` | R2 重复 lowM direct8 |
| G2 vs G4 | 精度路线（direct8 vs PR） | `B_Q2_k8_lowM` vs `B_Q2_k8_lowM_PR_tp14` | R2 重复 lowM direct8 |
| G1 vs G3 | 精度路线（direct8 vs PR，均为 M0） | `B_Q2_k8` vs G3 | G3 |
| G3 vs G4 | 罚项 M（M0 vs lowM，均为 PR） | G3 vs `B_Q2_k8_lowM_PR_tp14` | G3 |

只有“实际设备相同”时才能写成受控；否则标注非完全受控。

## 3. 重复候选与标记

| 候选 | 矩阵哈希 | 历史任务 | 重复保护 | 标记 |
|---|---|---|---|---|
| `T004_R2_intentional_repeat_Q2_lowM_direct8` | `34f84ed6…` | `B_Q2_k8_lowM` | 会触发 matrix 冲突 | 任务名含 `intentional_repeat`；需 `--allow-matrix-reuse` |
| `T004_R2_intentional_repeat_Q2_lowM_PR_tp14` | `d4f6e0ff…` | `B_Q2_k8_lowM_PR_tp14` | 会触发 matrix 冲突 | 同上 |

- 不修改矩阵或参数绕过重复保护。
- 授权与实验目的人工记录在 `FINAL_SUBMISSION_PLAN.md`；提交时逐字确认任务编号。
- 每个重复候选只执行 1 次；不根据结果追加参数搜索。

## 4. 统计口径

- 任务级：每个任务是否严格命中原始最优（0/1），不把样本比例当任务成功率。
- 样本级：严格有效样本数 / 返回数；PR 仅拆分一致 + one-hot 合法计入严格有效。
- 少量重复只能报告“本次任务是否重复命中”，不能估计长期稳定命中概率。
