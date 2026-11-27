# 原始实验环境对齐报告（Phase 10 补充）

- 时间：2026-11-27（Asia/Shanghai）
- 目标：用队友提供的直接依赖清单建立独立环境，解除“原始依赖版本未知”的阻塞
- 状态：**PARTIAL PASS** —— Python 版本与 9 个直接依赖可精确匹配；操作系统不同，传递依赖仅本地有、队友未提供
- 边界：未修改任何模型、算法、参数、随机种子或科学结论；未提交真机任务；未消耗配额

---

## 1. 原始材料归档

| 文件 | 字节 | SHA256 | 来源 |
|---|---:|---|---|
| `REPRO_NOTES.md` | 3,245 | `e601b556…ffc9c9` | 队友微信提供 |
| `requirements.txt` | 181 | `fe0fd99f…b9f479` | 同上 |
| `same_protocol_metrics.json` | 233 | `20a68f7d…0728e7` | 同上 |

三份文件原样复制到 `docs/reproduction/original_environment/`，未做内容修改；完整哈希见同目录 `MANIFEST.json`。

---

## 2. 环境创建

| 项目 | 值 |
|---|---|
| 环境路径 | `%LOCALAPPDATA%\kaiwu-original` |
| 解释器 | 独立 CPython 3.12.5（python-build-standalone，uv 管理） |
| 平台 | `Windows-10-10.0.19045-SP0` |
| pip | 26.3 |
| 安装命令 | `python -m pip install -r requirements.txt --no-cache-dir` |
| 安装日志 | `install.log` |
| 包索引 | 本机 pip 配置的清华镜像（仅影响下载来源，版本由 requirements 锁定） |

创建过程中的既有问题（已绕开，未修改）：Anaconda 自带的 Python 3.12.5 执行 `import pyexpat` 报
`DLL load failed: 拒绝访问`，导致 `venv` 的 ensurepip 失败。为不破坏现有 Anaconda，改用 uv 安装
独立 CPython 3.12.5 建立环境。该问题属于本机 Anaconda 的既有状态，未做任何修复或覆盖。

---

## 3. 直接依赖对照

| 包 | 队友要求 | `requirements.lock.txt`（kaiwu-verify） | `kaiwu-original` 实测 | 判定 |
|---|---:|---:|---:|---|
| numpy | 2.4.4 | 2.5.5 | 2.4.4 | 新环境已对齐 |
| pandas | 2.2.3 | 2.2.3 | 2.2.3 | 一致 |
| scikit-learn | 1.8.0 | 1.9.1 | 1.8.0 | 新环境已对齐 |
| xgboost | 3.4.1 | 3.4.1 | 3.4.1 | 一致 |
| lightgbm | 4.7.0 | 未安装 | 4.7.0 | 新环境新增 |
| mendeleev | 1.4.0 | 1.4.0 | 1.4.0 | 一致 |
| scipy | 1.17.1 | 1.18.1 | 1.17.1 | 新环境已对齐 |
| matplotlib | 3.10.3 | 3.10.3 | 3.10.3 | 一致 |
| kaiwu | 1.4.4 | 1.4.4 | 1.4.4 | 一致 |

结论：9 个直接依赖全部按队友要求安装成功；与 `kaiwu-verify` 的差异是 3 个版本（numpy / scikit-learn / scipy）+ 新增 lightgbm。

---

## 4. 全量包差异（kaiwu-verify 54 包 vs kaiwu-original 55 包）

| 类别 | 包 | 变化 |
|---|---|---|
| 仅新环境 | lightgbm | 未安装 → 4.7.0 |
| 版本不同 | numpy | 2.5.5 → 2.4.4 |
| 版本不同 | scikit-learn | 1.9.1 → 1.8.0 |
| 版本不同 | scipy | 1.18.1 → 1.17.1 |

除上述 4 项外，其余 51 个传递依赖版本完全一致（kaiwu 1.4.4、kaiwu-community 1.0.8、pandas 2.2.3、xgboost 3.4.1、mendeleev 1.4.0、matplotlib 3.10.3、joblib 1.6.0 等）。

完整锁定：`requirements.freeze.txt`（55 行）。

---

## 5. 兼容性与导入检查

`python -m pip check`：**No broken requirements found.**（输出见 `pip_check.txt`）

模块导入（详见 `import_check.json`）：

| 模块 | 导入 | 版本 |
|---|---|---|
| numpy | OK | 2.4.4 |
| pandas | OK | 2.2.3 |
| sklearn | OK | 1.8.0 |
| xgboost | OK | 3.4.1 |
| lightgbm | OK | 4.7.0 |
| mendeleev | OK | 1.4.0 |
| scipy | OK | 1.17.1 |
| matplotlib | OK | 3.10.3 |
| joblib | OK | 1.6.0 |
| kaiwu | OK | 1.4.4（`kw.__version__` 显示 1.0.8） |

`kw.__version__` 来自 `kaiwu-community`，真实版本应读 `importlib.metadata.version("kaiwu")`，与队友说明一致。

在新环境运行既有工程自检：

```text
python code/verify_project.py
PASS 15 | FAIL 0 | BLOCKED 0 | WARN 0
```

（完整输出：`verify_project_original_env.txt`。dry-run 未触发 license、未创建云端任务。）

安装日志中有一条非阻塞告警：pip 的 post-install 字节码编译在 `joblib/test/test_func_inspect_special_encoding.py`
上触发 `BlockedImportError: encodings.big5`。该文件是 joblib 的测试文件，不影响 `joblib` 本体导入
（已实测 OK），也不影响 `pip check` 与工程自检。`install.log` 仅保留关键事件，完整解析器日志未入库。

---

## 6. License 与环境保护

| 检查 | 结果 |
|---|---|
| `kaiwu-verify` 是否被修改 | 未修改：`pip freeze` 与该环境 `requirements.lock.txt` 逐包一致（54/54） |
| `kaiwu-verify` 的 kaiwu 版本 | 1.4.4（未降级、未覆盖） |
| 新环境是否独立 | 是，独立 venv，Python 3.12.5 |
| 新环境授权状态 | 常见用户目录下未发现授权文件；未执行 `license.init`，未读取或打印任何凭据 |
| 真机接口 | 未调用；未提交任务；未消耗配额 |

如需真机实验，仍由账号持有人在交互终端执行 `d_submit_cim.py --init`；本补充任务不触碰授权。

---

## 7. 与队友环境的差异（不得宣称完全相同）

| 维度 | 队友原始环境 | 本次对齐环境 | 判定 |
|---|---|---|---|
| Python 精确版本 | 3.12.5 | 3.12.5 | 一致 |
| 操作系统 | Windows 11 | Windows 10 企业版 22H2（19045） | **不一致** |
| 直接依赖 | 9 项 | 9 项逐项一致 | 一致 |
| 传递依赖 | 未提供 | 本地 `pip freeze` 55 项 | 无法逐包核对 |
| CPU/GPU/驱动 | 未提供 | 本机 | 无法核对 |

结论：这是“同 Python 版本、同直接依赖版本、不同操作系统”的复现环境。任何数值差异都不能单独归因于依赖版本，也不能把本环境称为“与队友环境完全相同”。

---

## 8. 复现执行

复现工作目录与运行说明：`reproduction/original_env_20261127/README.md`。

- 脚本：`reproduction/original_env_20261127/run_reproduction.ps1`
- 行为：把 `code/` 与 `date/` 复制到独立临时目录后运行 `run_all.py`，不覆盖仓库历史产物
- 正式复跑与结果核验：**由参赛队员执行**
- 三种口径：`docs/reproduction/PROTOCOLS.md`（02→03 验证 / 分组 OOF / 04 官方盲测）

---

## 9. 限制与未解决项

1. 操作系统无法匹配 Windows 11；本机为 Windows 10 19045。
2. 队友只提供 9 个直接依赖，传递依赖版本仍未提供；本地 freeze 只能证明本环境，不等于队友环境。
3. 队友的 `same_protocol_metrics.json` 只含分组 OOF 与池标签统计，不含 02→03 明细与 04 盲测指标。
4. 04 官方盲测集无 `V` 列，本地无法计算任何监督指标。
5. 本报告不判断数值差异来源；差异是否可接受由参赛队员决定。
