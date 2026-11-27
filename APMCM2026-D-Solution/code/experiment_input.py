# -*- coding: utf-8 -*-
"""实验输入版本管理（Phase 10）。

设计目标：
1. 每次实验必须显式选择一个输入版本，不做隐式默认。
2. 登记时把输入冻结到 ``experiments/inputs/<version>/`` 并记录 SHA256。
3. 加载时逐文件复核哈希；输入被改动则拒绝运行，必须登记为新版本。
4. 原始预测（official_prediction）与独立复现（independent_reproduction）不得混用。
5. 本模块只做格式读取、校验与哈希，不生成、不修改任何赛题数学模型。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from paths import ROOT

SCHEMA_VERSION = 1

# 允许的输入来源类型。前三种互斥，teaching 仅用于测试。
INPUT_KINDS = {
    "team_model": "参赛队员提供的已确认模型产物",
    "official_prediction": "仓库内既有代理模型预测文件（code/predictions/）",
    "independent_reproduction": "独立复现产物（results/reproduction_*/）",
    "teaching": "非赛题教学矩阵，仅用于工程测试",
}

MIXED_FORBIDDEN = ("official_prediction", "independent_reproduction")

_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def experiments_root() -> Path:
    """实验根目录；测试可通过环境变量隔离到临时目录。"""
    return Path(os.environ.get("APMCM_EXPERIMENT_ROOT", str(ROOT / "experiments"))).resolve()


def inputs_root() -> Path:
    return experiments_root() / "inputs"


def tasks_root() -> Path:
    return experiments_root() / "tasks"


def config_root() -> Path:
    return experiments_root() / "config"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def matrix_sha256(A, B, V) -> str:
    """矩阵语义哈希：标签顺序 + float64 数值。用于输入版本与重复任务判定。"""
    arr = np.ascontiguousarray(np.asarray(V, dtype=np.float64))
    h = hashlib.sha256()
    h.update(b"apmcm-matrix-v1\0")
    h.update(("\x1f".join(map(str, A)) + "\x1e" + "\x1f".join(map(str, B))).encode("utf-8"))
    h.update(str(arr.shape).encode("ascii"))
    h.update(np.round(arr, 12).tobytes())
    return h.hexdigest()


def numeric_matrix_sha256(mat) -> str:
    """纯数值矩阵哈希，用于“实际提交的 Ising 矩阵”。"""
    arr = np.ascontiguousarray(np.asarray(mat, dtype=np.float64))
    h = hashlib.sha256()
    h.update(b"apmcm-ising-v1\0")
    h.update(str(arr.shape).encode("ascii"))
    h.update(arr.tobytes())
    return h.hexdigest()


def detect_kind(path: Path) -> str:
    """按路径推断来源类型；无法判断时视为队员提供。"""
    s = str(path).replace("\\", "/").lower()
    if "/results/reproduction_" in s or s.startswith("results/reproduction_"):
        return "independent_reproduction"
    if "/code/predictions/" in s or s.startswith("code/predictions/"):
        return "official_prediction"
    return "team_model"


def _now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def _fail(msg: str) -> None:
    raise SystemExit(f"[输入版本] {msg}")


@dataclass(frozen=True)
class ExperimentInput:
    version: str
    kind: str
    A: list = field(default_factory=list)
    B: list = field(default_factory=list)
    V: np.ndarray = None
    matrix_sha256: str = ""
    files: dict = field(default_factory=dict)
    sub_question: str = ""
    x_value: str = None
    value_column: str = "V_hat"
    value_semantics: str = "lower_is_better"
    source_paths: list = field(default_factory=list)
    notes: str = ""
    dir: Path = None

    @property
    def shape(self):
        return (len(self.A), len(self.B))


def _read_matrix_file(path: Path, fmt: str, value_col: str, a_col: str, b_col: str,
                      x_col: str, x_value: str):
    """读取矩阵：fmt=matrix（带行列标签的方阵）或 fmt=long（A,B,...,value 长表）。"""
    if fmt == "matrix":
        if path.suffix.lower() == ".npz":
            data = np.load(path, allow_pickle=False)
            A = [str(v) for v in data["A"]]
            B = [str(v) for v in data["B"]]
            V = np.asarray(data["matrix"], dtype=np.float64)
        else:
            df = pd.read_csv(path, index_col=0)
            # 首列若是 "A" 之类的表头占位，pandas 已作为索引名；只取数据
            A = [str(v) for v in df.index]
            B = [str(v) for v in df.columns]
            V = df.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
    elif fmt == "long":
        df = pd.read_csv(path)
        for col in (a_col, b_col, value_col):
            if col not in df.columns:
                _fail(f"长表缺少列 {col}；现有列 {list(df.columns)}")
        if x_col:
            if x_col not in df.columns:
                _fail(f"长表缺少 X 列 {x_col}")
            if x_value is None:
                _fail("指定了 --x-col 但没有指定 --x 取值")
            df = df[df[x_col].astype(str) == str(x_value)]
            if df.empty:
                _fail(f"X={x_value} 过滤后没有数据")
        df = df.assign(**{a_col: df[a_col].astype(str), b_col: df[b_col].astype(str)})
        dup = df.duplicated([a_col, b_col]).sum()
        if dup:
            _fail(f"长表存在 {dup} 组重复 (A,B)，无法确定唯一矩阵")
        Vdf = df.pivot(index=a_col, columns=b_col, values=value_col)
        A = [str(v) for v in Vdf.index]
        B = [str(v) for v in Vdf.columns]
        V = Vdf.to_numpy(dtype=np.float64)
    else:
        _fail(f"未知格式 {fmt}，只支持 matrix / long")

    if V.size == 0:
        _fail("矩阵为空")
    if V.ndim != 2 or min(V.shape) < 2:
        _fail(f"矩阵形状不合法：{V.shape}")
    if not np.isfinite(V).all():
        miss = int((~np.isfinite(V)).sum())
        _fail(f"矩阵含 {miss} 个缺失或非有限值；请先由队员确认补全，工具不代为填充")
    if len(set(A)) != len(A) or len(set(B)) != len(B):
        _fail("行列标签存在重复")
    return A, B, V


def register(version: str, matrix_path: Path, fmt: str = "auto", kind: str = None,
             value_col: str = "V_hat", a_col: str = "A", b_col: str = "B",
             x_col: str = None, x_value: str = None, notes: str = "",
             sub_question: str = "", value_semantics: str = "lower_is_better") -> Path:
    """登记输入版本：冻结文件、计算哈希、写 manifest。拒绝覆盖已有版本。"""
    if not _VERSION_RE.match(version):
        _fail(f"版本名不合法：{version}（仅允许字母数字 . _ -，最长 64）")

    matrix_path = Path(matrix_path)
    if not matrix_path.is_absolute():
        matrix_path = (ROOT / matrix_path).resolve()
    if not matrix_path.is_file():
        _fail(f"矩阵文件不存在：{matrix_path}")

    if fmt == "auto":
        fmt = "matrix" if matrix_path.suffix.lower() in (".csv", ".npz") and \
            matrix_path.name.lower().startswith(("matrix", "ising")) else "long"
        if matrix_path.suffix.lower() == ".npz":
            fmt = "matrix"

    detected = detect_kind(matrix_path)
    if kind is None:
        kind = detected
    if kind not in INPUT_KINDS:
        _fail(f"未知来源类型 {kind}；可选 {sorted(INPUT_KINDS)}")
    if kind in MIXED_FORBIDDEN and detected != kind:
        _fail(f"来源类型冲突：声明 {kind}，但路径特征指向 {detected}。"
              f"原始预测与独立复现不得混用。")

    vdir = inputs_root() / version
    manifest_path = vdir / "manifest.json"
    if manifest_path.exists():
        _fail(f"版本 {version} 已存在且已登记。历史版本不覆盖，请换一个新版本名。")
    vdir.mkdir(parents=True, exist_ok=True)

    A, B, V = _read_matrix_file(matrix_path, fmt, value_col, a_col, b_col, x_col, x_value)

    # 冻结为统一的 matrix.csv（带行列标签）
    frozen_matrix = vdir / "matrix.csv"
    pd.DataFrame(V, index=A, columns=B).to_csv(frozen_matrix, encoding="utf-8-sig")

    mapping = {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "sub_question": sub_question,
        "x_value": x_value,
        "value_column": value_col,
        "value_semantics": value_semantics,
        "A_axis": "row",
        "B_axis": "column",
        "source_format": fmt,
        "notes": notes,
    }
    frozen_mapping = vdir / "mapping.json"
    frozen_mapping.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    source_manifest = {
        "schema_version": SCHEMA_VERSION,
        "original_matrix_path": str(matrix_path),
        "detected_kind": detected,
        "source_format": fmt,
        "filters": {"x_column": x_col, "x_value": x_value,
                    "value_column": value_col, "a_column": a_col, "b_column": b_col},
    }
    frozen_source = vdir / "source_manifest.json"
    frozen_source.write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    mhash = matrix_sha256(A, B, V)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "kind": kind,
        "created_at": _now(),
        "sub_question": sub_question,
        "x_value": x_value,
        "value_column": value_col,
        "value_semantics": value_semantics,
        "shape": [len(A), len(B)],
        "matrix_sha256": mhash,
        "files": {
            "matrix.csv": sha256_file(frozen_matrix),
            "mapping.json": sha256_file(frozen_mapping),
            "source_manifest.json": sha256_file(frozen_source),
        },
        "source_paths": [str(matrix_path)],
        "notes": notes,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return vdir


def load(version: str) -> ExperimentInput:
    """加载并复核输入版本；任何哈希不一致都拒绝运行。"""
    vdir = inputs_root() / version
    manifest_path = vdir / "manifest.json"
    if not manifest_path.is_file():
        _fail(f"输入版本不存在：{version}（{manifest_path}）")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("schema_version") != SCHEMA_VERSION:
        _fail(f"manifest schema 版本不支持：{manifest.get('schema_version')}")
    kind = manifest.get("kind")
    if kind not in INPUT_KINDS:
        _fail(f"manifest 来源类型非法：{kind}")

    bad = []
    for rel, expected in manifest.get("files", {}).items():
        p = vdir / rel
        if not p.is_file():
            bad.append(f"{rel}: 缺失")
        elif sha256_file(p) != expected:
            bad.append(f"{rel}: 哈希不一致")
    if bad:
        _fail("输入文件已被改动，拒绝运行（历史版本不覆盖，请登记新版本）：\n  - "
              + "\n  - ".join(bad))

    mapping = json.loads((vdir / "mapping.json").read_text(encoding="utf-8"))
    A, B, V = _read_matrix_file(vdir / "matrix.csv", "matrix", mapping.get("value_column", "V_hat"),
                                "A", "B", None, None)
    mhash = matrix_sha256(A, B, V)
    if mhash != manifest.get("matrix_sha256"):
        _fail("矩阵语义哈希与 manifest 不一致（文件可能被等价但不安全的改写）")

    return ExperimentInput(
        version=version, kind=kind, A=A, B=B, V=V, matrix_sha256=mhash,
        files=manifest.get("files", {}), sub_question=manifest.get("sub_question", ""),
        x_value=manifest.get("x_value"), value_column=manifest.get("value_column", "V_hat"),
        value_semantics=manifest.get("value_semantics", "lower_is_better"),
        source_paths=manifest.get("source_paths", []), notes=manifest.get("notes", ""), dir=vdir,
    )


def list_versions() -> list:
    out = []
    root = inputs_root()
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        mf = d / "manifest.json"
        if mf.is_file():
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))
                out.append({
                    "version": m.get("version", d.name), "kind": m.get("kind"),
                    "shape": m.get("shape"), "created_at": m.get("created_at"),
                    "sub_question": m.get("sub_question"), "matrix_sha256": m.get("matrix_sha256"),
                    "notes": m.get("notes"),
                })
            except Exception as e:  # 只影响列表展示
                out.append({"version": d.name, "kind": "ERROR", "error": str(e)})
    return out


def assert_single_kind(versions) -> str:
    """确认一组输入版本来源类型一致；禁止原始预测与独立复现混用。"""
    kinds = {load(v).kind if isinstance(v, str) else v.kind for v in versions}
    if len(kinds) > 1 and kinds & set(MIXED_FORBIDDEN):
        _fail(f"禁止混用不同来源的输入：{sorted(kinds)}")
    if len(kinds) > 1:
        _fail(f"一次实验只能使用一个输入版本，收到：{sorted(kinds)}")
    return kinds.pop()
