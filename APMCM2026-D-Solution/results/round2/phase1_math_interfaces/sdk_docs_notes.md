# SDK 官方文档要点（本次核对用）

1. https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/precision.html
   - SPQC 仅支持 8 位整数范围 [-128,127]，限制作用于 Ising 矩阵系数。
   - QUBO→Ising：`J_ij = q_ij/4`，线性项场 + 辅助自旋。
   - `adjust_ising_matrix_precision` 是直接截断：整体线性缩放到目标位宽后四舍五入。
   - 官方明确：存在极端值时直接截断会造成严重精度损失，小系数被压成 1；复杂问题应优先动态范围压缩或变量拆分。
   - 动态范围压缩 `perform_precision_adaption_mutate` 在满足缩放条件时可保持最优解；变量拆分 `perform_precision_adaption_split` 可达到任意精度但增加比特。
2. https://kaiwu-sdk-docs.qboson.com/zh/latest/source/modules/kaiwu.preprocess.html
   - `adjust_ising_matrix_precision` 文档原文提示“调整后矩阵可能会有较大的精度损失，比如矩阵有一个数远大于其它数时，调整后矩阵精度损失严重无法使用”。
   - `calculate_ising_matrix_bit_width` 返回 precision/multiplier；本工作流用其 8bit 可表示性检查。
   - `perform_precision_adaption_mutate` / `perform_precision_adaption_split` / `PrecisionReducer` 是另外的机制，本工作流未使用。

本工作流实际使用：`adjust_ising_matrix_precision(I, 8)`（直接截断），未使用动态范围压缩或变量拆分。因此不能假设量化后原始最优一定保留。
