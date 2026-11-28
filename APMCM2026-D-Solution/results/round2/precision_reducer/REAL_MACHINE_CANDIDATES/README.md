# T003 真机候选（未授权、未提交）

- 分支：`research/precision-reducer`
- 状态：**候选 A（tp14）已获授权并完成 1 次真机；候选 B（tp12）未提交**
- 结果：`t20261128-161915-...`；10 返回、2 拆分一致、恢复合法 2/10、
  两者同时满足 1/10，**严格有效原始最优命中 1/10**（样本 0，H=−206404 与构造最优一致）。
  详见 `RESULTS.md`。
- 平台余额：账面 32/已用 7/剩余 25（本任务消耗 1），`verified=false`，平台 PDF 待补。

## 候选 A：`B_Q2_k8_lowM_PR_tp14`（推荐）

- 目的：验证 PrecisionReducer 在**保留原始最优**的精度下能否在真机返回该最优。
- 配置：`B-Q2-NO2`，topk=8，`mfactor=0.33826009024559534`；
  `precision_reducer(precision=8, target_bits=550, truncated_precision=14,
  only_feasible_solution=false)`。
- 规模：原始 Ising 17 → 扩展 **121**（新增 104 拆分自旋）；有效截断 13 位。
- 本地：原始最优构造态拆分一致；13 位截断保留 La-Zr（V=0）；
  SA 拆分一致率约 1/100，`solutions_feasible` 预计 0–1/10 返回。
- 哈希：
  - input `0001ed364b48bbe0fc9b580f2485c1aebb36c194e5901551532a0992a28a979e`
  - V semantic `4abbd63ce9054386c4fb62cb416c358b89f3f4e16d3437e8c33235c0836a4887`
  - raw I `8f714e44bc6fd06e41f8eeeba526907c6f7928772fed5a9438c7d5673aa1b386`
  - submitted/expanded `d4f6e0ff12ac469484f9ca6fd16100ac77de0395e724d24cc2aaffa50f5815b3`
  - variables `bbf29b21fed605a986a546116c298268892c1ffb95ca28424f4615934e76ad43`
- 风险：拆分一致率低，可能 0 合法返回；若返回合法但非 La-Zr，则说明扩展问题最优
  与原始目标不一致或搜索失败。
- 预期配额：1 次优化任务。

## 候选 B：`B_Q2_k8_lowM_PR_tp12`（仅工程/恢复链路）

- 目的：在较高拆分一致率下验证真机的“扩展矩阵 → 恢复 → 原始解码”链路。
- 配置：同输入/M；`truncated_precision=12`。
- 规模：17 → **62**（新增 45）；有效截断 **11 位**。
- 本地：11 位截断下 La-Zr 严格劣于最优 La-Hf（`H_b(La-Zr)−min = 0.356`），
  **不能用于验证原始最优保留**；SA 拆分一致率约 4–10/100。
- 哈希：
  - input / V / raw I 同上；
  - submitted/expanded `ef86d45518c0175b54b196a843eabdd0e36544e76486c432bf5c18e380906e4e`
  - variables `b48eaded022e0229dfcd20704fb2df07c19572f41474ea3c12f4eed280a66cdf`
- 风险：即使真机返回 V=0，也可能来自拆分不一致样本，不能作为保真证据。
- 预期配额：1 次优化任务。

## 共同提交前检查

- `d_experiment plan` 已通过；未调用 license、未创建云端任务、未写入归档。
- 矩阵 8bit 可表示（`calculate_ising_matrix_bit_width(...,8).precision=8`）。
- 扩展维度 62/121，低于 SPQC-550 的常见容量；平台实际容量需确认。
- 拆分映射状态 `verified_reconstruction`；`split_mapping.json` 将随任务归档。
- 单次 `PrecisionReducer.solve` 只触发一次组件求解，配额按 1 次估算。
- 提交命令（需队员逐字确认任务编号）：

```powershell
python code/d_experiment.py run --config results/round2/precision_reducer/REAL_MACHINE_CANDIDATES/B_Q2_k8_lowM_PR_tp14.json --submit
```

- 若提交后下载失败，使用 `resume --task-id`，不要重新提交。
