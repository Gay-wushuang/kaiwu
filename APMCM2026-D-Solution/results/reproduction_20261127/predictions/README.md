# 基线 B：独立复现预测文件

- 来源：`%TEMP%\apmcm_repro_original_20261127`（kaiwu-original，Python 3.12.5，队友 9 项直接依赖）
- 对应模型：`models/surrogate_phys.joblib`（SHA256 `ba22ec9e…`）
- 交付结果：同批次 `results/reproduction_20261127/`（3.12.6 复现，三个提交文件与本次 3.12.5 复现逐字节一致）
- 哈希：见 `SHA256SUMS.txt`

**禁止混用**：`code/predictions/` 是基线 A（队友原始预测），与本目录不是同一模型批次。二者 V̂ 最大差 4.733；选择基线时只能整套使用。

生成命令：`reproduction/original_env_20261127/run_reproduction.ps1`（只读运行，不覆盖历史结果）。
