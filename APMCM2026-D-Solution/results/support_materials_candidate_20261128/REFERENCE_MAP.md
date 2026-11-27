# 引用关系图

## 1. 版本时间线

- 基线 B 模型/预测：`822b7ea`（独立复现归档）
- 第一轮真机执行：`2a56c554f1a62561a883fe83f16d8c8a327b4357`（每个任务 `config.json` 内记录）
- 第二轮接口增强：`1768335`（不影响本轮数据）
- 本包打包基线：`577c83bd013f002df77282538b64185d027ad0c3`

## 2. 基线 B 模型 → 预测

| 对象 | 路径 | SHA256 |
|---|---|---|
| 模型 | `models/surrogate_phys.joblib`（未入包） | `ba22ec9ec9c7555c62d15f4bf543546ad99f2b445f800a25f2cabcd33c300357` |
| 预测 | `FORMAL/BASELINE_B/predictions/pool_q2_phys.csv` | `e818443c78480b680d273034c3620d0a5a2d6d2b4eba65d0375662bd858356fe` |
| 预测 | `FORMAL/BASELINE_B/predictions/pool_q2b_phys.csv` | `5898af30887ea249b814ed03e679b02efc3d7af2419a3fd49d635e51708b4bc1` |
| 预测 | `FORMAL/BASELINE_B/predictions/pool_q3_phys.csv` | `37c21d9dfa265640c46e58467666319af333d22bbb1208fb64ac561ea66d42ab` |
| 预测 | `FORMAL/BASELINE_B/predictions/pool_q3b_phys.csv` | `f362fa5a1bccbc37e2d66cb3da9baa38943e26c3cb73015bdf7bcf865c054c24` |

## 3. 输入版本 → 预测来源

| 输入 | 矩阵 SHA256 | 来源预测 | 执行任务 |
|---|---|---|---|
| B-Q2-NO2 | `0001ed364b48bbe0fc9b580f2485c1aebb36c194e5901551532a0992a28a979e` | pool_q2_phys.csv | B_Q2_baseline、B_Q2_m3x、B_Q2_k8 |
| B-Q3-O3 | `23908ae0adad088d2fed03e70fc7d48c01da770e28818e0503144405c3f6e423` | pool_q3_phys.csv | B_Q3_O3_baseline |
| B-Q3-FO2 | `ef4f5e512b5b4ef3860d5ec71fc67e0ccd478a666eb730b84ae578d8b6cefcf8` | pool_q3_phys.csv | B_Q3_FO2_baseline |
| B-Q3-NO2 | `0001ed364b48bbe0fc9b580f2485c1aebb36c194e5901551532a0992a28a979e` | pool_q3_phys.csv（未执行） | 未执行（与 B-Q2-NO2 同矩阵） |

## 4. 任务输入 source_manifest 映射

任务归档保留原始结构，未复制 `source_manifest.json`；以下集中输入副本与任务 `config.json` 记录的哈希一致。

| 任务 | 输入版本 | 任务 config 记录 SHA256 | 集中副本 | 副本 SHA256 | 一致 |
|---|---|---|---|---|---|
| B_Q2_baseline | B-Q2-NO2 | `d5bb963cf7ad25ac7d72f6ba88251601c97cee110609001b07fd8140a1e8354e` | `FORMAL/ROUND1/inputs/B-Q2-NO2/source_manifest.json` | `d5bb963cf7ad25ac7d72f6ba88251601c97cee110609001b07fd8140a1e8354e` | 是 |
| B_Q2_m3x | B-Q2-NO2 | `d5bb963cf7ad25ac7d72f6ba88251601c97cee110609001b07fd8140a1e8354e` | `FORMAL/ROUND1/inputs/B-Q2-NO2/source_manifest.json` | `d5bb963cf7ad25ac7d72f6ba88251601c97cee110609001b07fd8140a1e8354e` | 是 |
| B_Q2_k8 | B-Q2-NO2 | `d5bb963cf7ad25ac7d72f6ba88251601c97cee110609001b07fd8140a1e8354e` | `FORMAL/ROUND1/inputs/B-Q2-NO2/source_manifest.json` | `d5bb963cf7ad25ac7d72f6ba88251601c97cee110609001b07fd8140a1e8354e` | 是 |
| B_Q3_O3_baseline | B-Q3-O3 | `007768b3555164c47f709af2d2fd8cf080f2025740a4d43fb34155e4c4cf1041` | `FORMAL/ROUND1/inputs/B-Q3-O3/source_manifest.json` | `007768b3555164c47f709af2d2fd8cf080f2025740a4d43fb34155e4c4cf1041` | 是 |
| B_Q3_FO2_baseline | B-Q3-FO2 | `cfbfa63f6db0d56ad5825afb76b26043cdada790ff8b0a0a54eda69583e9961d` | `FORMAL/ROUND1/inputs/B-Q3-FO2/source_manifest.json` | `cfbfa63f6db0d56ad5825afb76b26043cdada790ff8b0a0a54eda69583e9961d` | 是 |
| B_Q2_baseline（license 提交前失败） | B-Q2-NO2 | `d5bb963cf7ad25ac7d72f6ba88251601c97cee110609001b07fd8140a1e8354e` | `FORMAL/ROUND1/inputs/B-Q2-NO2/source_manifest.json` | `d5bb963cf7ad25ac7d72f6ba88251601c97cee110609001b07fd8140a1e8354e` | 是 |

## 5. 第一轮任务 → 平台报告

| 任务 | 归档目录 | 状态 | 配额 | 平台任务 ID | 设备 | 硬件 | 报告 |
|---|---|---|---|---|---:|---|
| B_Q2_baseline | `FORMAL/ROUND1/tasks/t20261128-003014-b_q2_baseline-be06017f` | completed | 是 | 44923771c251417d91f15d9841651b4c | SPQC-550 | 1.0327 ms | `FORMAL/ROUND1/tasks/t20261128-003014-b_q2_baseline-be06017f/reports/B_Q2_baseline.pdf` |
| B_Q2_m3x | `FORMAL/ROUND1/tasks/t20261128-003124-b_q2_m3x-e2530a24` | completed | 是 | a8894d47ec774954ad2c0a3f99634eca | SPQC-550 | 13.9135 ms | `FORMAL/ROUND1/tasks/t20261128-003124-b_q2_m3x-e2530a24/reports/B_Q2_m3x.pdf` |
| B_Q2_k8 | `FORMAL/ROUND1/tasks/t20261128-003140-b_q2_k8-7be3225f` | completed | 是 | 6258685cdb1c4541becdb1ae40fac598 | SPQC-550 | 10.9816 ms | `FORMAL/ROUND1/tasks/t20261128-003140-b_q2_k8-7be3225f/reports/B_Q2_k8.pdf` |
| B_Q3_O3_baseline | `FORMAL/ROUND1/tasks/t20261128-003159-b_q3_o3_baseline-7cd9ce6b` | completed | 是 | 4a75fbffbe734857b87db54ed346c342 | SPQC-550 | 0.7838 ms | `FORMAL/ROUND1/tasks/t20261128-003159-b_q3_o3_baseline-7cd9ce6b/reports/B_Q3_O3_baseline.pdf` |
| B_Q3_FO2_baseline | `FORMAL/ROUND1/tasks/t20261128-003216-b_q3_fo2_baseline-ca295ce6` | completed | 是 | 87d51d0a3fa14434a80d3bcb63878348 | SPQC-550 | 1.2345 ms | `FORMAL/ROUND1/tasks/t20261128-003216-b_q3_fo2_baseline-ca295ce6/reports/B_Q3_FO2_baseline.pdf` |
| B_Q2_baseline（license 提交前失败） | `FORMAL/ROUND1/tasks/t20261128-001932-b_q2_baseline-be06017f` | submit_failed | 否 | — | — | — | — |

## 6. 基线 A（历史对照，未入包）

见 `HISTORICAL/BASELINE_A_REFERENCE.md`。基线 A 的预测/真机报告与 B 不同批次，禁止混引。
