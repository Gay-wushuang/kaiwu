# -*- coding: utf-8 -*-
"""项目路径统一入口。

所有脚本通过本模块定位资源：路径一律相对仓库根目录解析，
不依赖当前工作目录，也不写死本机绝对路径。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
DATA = ROOT / "date"
PRED = CODE / "predictions"
RES = ROOT / "results"
FIG = ROOT / "figures"
MODELS = ROOT / "models"
LOGS = RES / "logs"
CIM_STATS = RES / "cim_stats"
CIM_SAMPLES = RES / "cim_samples"

# 赛题附件（行数以赛题 PDF 表 3 为准，见 docs/ENGINEERING_ACCEPTANCE.md）
DATA_FILES = (
    "02_castelli_train.csv",
    "03_castelli_val.csv",
    "04_castelli_test_holdout.csv",
    "06_castelli_no_physics.csv",
    "07_castelli_q2_pool.csv",
    "08_castelli_q3_pool.csv",
    "11_castelli_q2_pool_blind.csv",
    "12_castelli_q3_pool_blind.csv",
)


def _block(paths):
    return "\n".join(f"  - {p}" for p in paths)


def require_data(*names):
    """确认赛题附件存在；缺失时打印明确路径并以非零码退出。"""
    paths = [DATA / n for n in (names or DATA_FILES)]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise SystemExit(
            "[缺少输入数据] 以下赛题附件不存在：\n"
            + _block(missing)
            + f"\n请把附件 CSV 放到 {DATA} 后重试（说明见 README「数据说明」）。"
        )
    return paths


def require_files(paths, what="输入文件"):
    """确认任意输入文件存在；缺失时打印明确路径并以非零码退出。"""
    paths = [Path(p) for p in paths]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise SystemExit(
            f"[缺少{what}] 以下文件不存在：\n"
            + _block(missing)
            + "\n请先补齐输入或检查路径配置。"
        )
    return paths


def ensure_output_dirs():
    """创建可写输出目录（不创建 date/，数据目录必须由使用者提供）。"""
    for d in (RES, FIG, MODELS, PRED, CIM_STATS, CIM_SAMPLES):
        d.mkdir(parents=True, exist_ok=True)
