# 已知问题与版本边界

以下问题只记录，不改原始文件；由队员确认论文/支撑材料如何引用。

1. **`FINAL_ANSWERS.md` 包内为修订件**：原件末行“真机实验（3 次配额已用完）”对应基线 A 的 3 个历史任务，不是基线 B 的第一轮 5 个任务。包内 `FINAL_ANSWERS.md` 仅删除该末行，正文未添加任何说明文字，数值、表格与答案未改；原文保留为 `FINAL_ANSWERS_ORIGINAL.md`，来源哈希与修订说明见 `REVISIONS.md`。B 真机结果只引用 `FORMAL/ROUND1/ROUND1_REAL_MACHINE_REPORT.md`。
2. **根目录 `README.md` 的“关键结果”表混有 A/B 两套数字**（如 R²=0.831 与 0.825、LaHfO₂N 与 LaZrO₂N）。该文件未收入本包；论文引用 B 时只使用 `FORMAL/BASELINE_B/`。
3. **基线 A/B 预测不同批次**：同名预测池最大 |ΔV| = 4.733；本包只含 B。`code/predictions/` 与 `results/vendor_reports/` 属 A，未复制。
4. **`results/EXPERIMENT_INDEX.md` 是基线 A 索引**，其中 3 个任务与 MISSING 标记不适用于 B；本包未复制。
5. **模型产物未入包**：`models/surrogate_phys.joblib` 约 15 MB，`.gitignore` 排除；哈希 `ba22ec9ec9c7555c62d15f4bf543546ad99f2b445f800a25f2cabcd33c300357`，可由 `run_all.py` 重新生成。
6. **`sdk_checkpoints/*.pkl` 未入包**：SDK 检查点缓存共 5 个，`.gitignore` 排除；原始解向量已由 `raw/solutions.npz` 与平台 PDF 保存。
7. **第一轮任务 `config.json` 中 `git_dirty=true`**：执行时任务归档尚未提交，代码提交为 `2a56c55`；不代表算法改动。
8. **`V̂` 是代理模型预测违反度，不是真实物理违反度**；论文不得写成实测物理量。
9. **合法最优 ≠ 全 Ising 空间全局最优**：真机 H 是 8-bit 适配矩阵上的合法 one-hot 能量；报告已按此口径。
10. **Q3 NO2 输入已登记但未执行**：与 `B-Q2-NO2` 同矩阵，第一轮按要求未重复提交。
11. **配额为本地账本**：32 总 / 5 已用 / 27 剩余；平台余额以控制台为准。
12. **04 官方盲测集无标签**，不能本地声称 R²/MAE 已验证。
