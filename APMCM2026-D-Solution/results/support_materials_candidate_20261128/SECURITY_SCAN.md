# 安全扫描

- 扫描范围：本包全部文本文件（163 个）。
- 未发现 `license.lic` / `auth.json` / `*.pem` / `*.key` / 凭据文件。
- 未发现 `sdk_code`、`user_id`、`authorization`、`password`、`api_key`、`secret` 的**实际取值**。
- 未发现 `*.pkl`、`sdk_checkpoints/`、`__pycache__/`、`models/`、`date/`。
- 说明：`AI_USAGE_LOG.md` 与失败记录的 `task.json` / `attempts.jsonl` 仅出现字段名（如 `user_id` / `sdk_code`）用于说明“未输入/未记录”，不含任何值；这是原始记录的如实保留，不是凭据。
- 未复制平台账号、密码、SDK Code、License 文件内容。
