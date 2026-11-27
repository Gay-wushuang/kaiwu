# -*- coding: utf-8 -*-
"""实验任务归档与本地任务注册表（Phase 10）。

约束：
1. 每个任务一个独立目录，历史归档只读，不覆盖。
2. 只保存原始返回与机械可核对的元数据；不重算、不替换任何科学结论。
3. 凭据类字段（authorization / token / sdk_code / user_id）一律不落盘。
"""
from __future__ import annotations

import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from paths import ROOT
from experiment_input import (
    ExperimentInput,
    experiments_root,
    numeric_matrix_sha256,
    sha256_file,
    tasks_root,
)

SCHEMA_VERSION = 1

STATUS_TEXT = {
    "created": "归档已建立，尚未提交",
    "submit_failed": "提交失败（未创建云端任务）",
    "submitted": "已提交，等待结果",
    "run_failed": "云端运行失败",
    "download_failed": "任务完成但结果下载失败",
    "unknown_failure": "未知阶段失败（保守按已提交计）",
    "invalid_result": "返回解格式非法（原样归档，未采信）",
    "completed": "结果已归档",
    "resume_no_result": "恢复时未取到结果",
    "cancelled": "用户取消，未提交",
    "dry_run": "仅计划，未提交",
}

# 这些状态代表云端任务已创建，应按保守口径计入本地配额消耗
QUOTA_COUNTED_STATUS = {"submitted", "run_failed", "download_failed", "completed", "resume_no_result"}

_FORBIDDEN_KEYS = {"authorization", "_authorization", "sdk_code", "user_id", "token", "password",
                   "secret", "api_key"}


def now_str() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def registry_path() -> Path:
    return experiments_root() / "registry.json"


def git_info() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True,
                                text=True, timeout=10).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                                    capture_output=True, text=True, timeout=10).stdout.strip())
        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(ROOT),
                                capture_output=True, text=True, timeout=10).stdout.strip()
        return {"git_commit": commit or None, "git_branch": branch or None, "git_dirty": dirty}
    except Exception as e:
        return {"git_commit": None, "git_branch": None, "git_dirty": None, "git_error": str(e)}


def sdk_info() -> dict:
    try:
        return {"sdk_version": importlib.metadata.version("kaiwu"),
                "python_version": platform.python_version()}
    except Exception:
        return {"sdk_version": None, "python_version": platform.python_version()}


def json_safe(obj):
    """把 numpy / Path / 其他对象转成可 JSON 序列化的结构；数组保留为嵌套列表。"""
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()
                if str(k).lower() not in _FORBIDDEN_KEYS}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return repr(obj)


def slugify(text: str, limit: int = 28) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text)).strip("-")
    return (s[:limit] or "task").lower()


def validate_spin_matrix(solutions, n_bits: int) -> np.ndarray:
    """校验返回解：二维、列数等于 Ising 比特数、取值只能为 ±1。

    只做格式校验，不解释物理含义；异常时抛出 ValueError，由调用方决定如何归档。
    """
    arr = np.atleast_2d(np.asarray(solutions))
    if arr.ndim != 2:
        raise ValueError(f"返回解不是二维数组：shape={arr.shape}")
    if arr.shape[1] != int(n_bits):
        raise ValueError(f"返回解列数 {arr.shape[1]} != Ising 比特数 {n_bits}")
    if arr.size == 0:
        raise ValueError("返回解为空")
    values = np.unique(arr)
    if not np.all(np.isin(values, (-1, 1))):
        raise ValueError(f"返回解存在非 ±1 取值：{values[:10]}")
    return arr.astype(int)


def backup_if_exists(path) -> Path:
    """写入前备份已有文件，返回备份路径；不存在时返回 None。

    用于历史脚本的输出文件，避免重跑时静默覆盖旧结果。
    """
    p = Path(path)
    if not p.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = p.with_name(f"{p.stem}.bak-{stamp}{p.suffix}")
    shutil.copy2(p, backup)
    return backup


def make_task_id(task_name: str, matrix_hash: str, registry: "Registry" = None) -> str:
    base = f"t{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(task_name)}-{matrix_hash[:8]}"
    tid = base
    n = 2
    existing = {t["task_id"] for t in (registry.tasks if registry else [])}
    while tid in existing or (tasks_root() / tid).exists():
        tid = f"{base}-{n}"
        n += 1
    return tid


class Registry:
    """experiments/registry.json 的读写封装（单机单用户，不做并发锁）。"""

    def __init__(self):
        self.path = registry_path()
        self.tasks = []
        self._load()

    def _load(self):
        if self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.tasks = data.get("tasks", [])
            except Exception:
                self.tasks = []

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": SCHEMA_VERSION, "updated_at": now_str(), "tasks": self.tasks}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, entry: dict):
        self.tasks.append(entry)
        self.save()

    def get(self, task_id: str):
        for t in self.tasks:
            if t.get("task_id") == task_id:
                return t
        return None

    def update(self, task_id: str, **fields):
        for t in self.tasks:
            if t.get("task_id") == task_id:
                t.update(fields)
                t["updated_at"] = now_str()
                break
        self.save()

    def find_duplicate(self, task_name: str, ising_sha256: str, sdk_matrix_hash: str = None):
        """返回与本次任务冲突的历史记录；None 表示无冲突。

        提交失败/用户取消的任务从未创建云端任务、不消耗配额，允许原样重试。
        """
        for t in self.tasks:
            if t.get("status") in ("submit_failed", "cancelled"):
                continue
            same_name = t.get("task_name") == task_name
            same_matrix = (t.get("submitted_matrix_sha256") == ising_sha256 or
                           (sdk_matrix_hash and t.get("sdk_matrix_hash") == sdk_matrix_hash))
            if same_name and same_matrix:
                return t, "task_name_and_matrix"
            if same_matrix:
                return t, "matrix"
        return None, None

    def quota_consumed(self, mode_key: str) -> int:
        return sum(int(t.get("quota_units") or 0) for t in self.tasks
                   if t.get("mode_key") == mode_key and t.get("quota_counted"))


class TaskArchive:
    """单个任务的归档目录。创建后任何写操作都不得覆盖已有原始文件。"""

    def __init__(self, task_id: str, root: Path = None):
        self.task_id = task_id
        self.dir = (root or tasks_root()) / task_id
        self.meta_path = self.dir / "task.json"

    # ---------------------------------------------------------------- 创建
    @classmethod
    def create(cls, task_id: str, config: dict, exin: ExperimentInput, ising_matrix: np.ndarray,
               extra: dict = None, raw_ising_matrix: np.ndarray = None,
               submitted_A=None, submitted_B=None, filtered_V=None) -> "TaskArchive":
        arc = cls(task_id)
        if arc.dir.exists():
            raise SystemExit(f"[归档] 任务目录已存在，拒绝覆盖：{arc.dir}")
        for sub in ("input", "raw", "logs", "sdk_checkpoints", "reports"):
            (arc.dir / sub).mkdir(parents=True, exist_ok=True)

        cfg = dict(config)
        cfg.update(git_info())
        cfg.update(sdk_info())
        cfg.update({
            "task_id": task_id,
            "created_at": now_str(),
            "input_version": exin.version,
            "input_kind": exin.kind,
            "input_matrix_sha256": exin.matrix_sha256,
            "input_shape": list(exin.shape),
            "input_files": exin.files,
            "submitted_matrix_sha256": numeric_matrix_sha256(ising_matrix),
            "ising_shape": list(np.asarray(ising_matrix).shape),
        })
        if extra:
            cfg.update(extra)
        (arc.dir / "config.json").write_text(
            json.dumps(json_safe(cfg), ensure_ascii=False, indent=2), encoding="utf-8")

        # 输入快照（复制已冻结的输入，不引用原目录）
        for name in ("matrix.csv", "mapping.json", "manifest.json"):
            src = exin.dir / name
            if src.is_file():
                shutil.copy2(src, arc.dir / "input" / name)
        np.savetxt(arc.dir / "input" / "ising_matrix.csv", np.asarray(ising_matrix, dtype=np.float64),
                   delimiter=",", fmt="%.10g")
        hashes = {
            "input_files": exin.files,
            "input_matrix_sha256": exin.matrix_sha256,
            "ising_matrix_sha256": numeric_matrix_sha256(ising_matrix),
            "ising_matrix_csv_sha256": sha256_file(arc.dir / "input" / "ising_matrix.csv"),
        }
        if raw_ising_matrix is not None:
            np.savetxt(arc.dir / "input" / "ising_matrix_raw.csv",
                       np.asarray(raw_ising_matrix, dtype=np.float64), delimiter=",", fmt="%.10g")
            raw_npz = arc.dir / "input" / "ising_matrix_raw.npz"
            np.savez(raw_npz, matrix=np.asarray(raw_ising_matrix, dtype=np.float64))
            readback = np.load(raw_npz, allow_pickle=False)["matrix"]
            h_raw = numeric_matrix_sha256(raw_ising_matrix)
            h_read = numeric_matrix_sha256(readback)
            if h_read != h_raw:
                raise SystemExit("[归档] 原始浮点 Ising 矩阵二进制回读哈希不一致，已中止。")
            hashes.update({
                "raw_ising_matrix_sha256": h_raw,
                "raw_ising_matrix_csv_sha256": sha256_file(arc.dir / "input" / "ising_matrix_raw.csv"),
                "raw_ising_matrix_npz_sha256": sha256_file(raw_npz),
                "raw_ising_matrix_readback_sha256": h_read,
            })
            cfg.update({
                "raw_ising_matrix_sha256": h_raw,
                "raw_ising_shape": list(np.asarray(raw_ising_matrix).shape),
            })
            (arc.dir / "config.json").write_text(
                json.dumps(json_safe(cfg), ensure_ascii=False, indent=2), encoding="utf-8")

        # 实际提交映射：topk 预筛后 A/B 顺序、辅助自旋、变量索引、筛选后的 V
        if (submitted_A is None) != (submitted_B is None) or \
                (submitted_A is None) != (filtered_V is None):
            raise SystemExit("[归档] submitted_A/submitted_B/filtered_V 必须同时提供。")
        if submitted_A is not None:
            A = [str(v) for v in submitted_A]
            B = [str(v) for v in submitted_B]
            V = np.asarray(filtered_V, dtype=np.float64)
            nA, nB = len(A), len(B)
            n_qubo, n_ising = nA + nB, int(np.asarray(ising_matrix).shape[0])
            aux = n_ising - n_qubo
            if V.shape != (nA, nB):
                raise SystemExit(f"[归档] 筛选后 V 形状 {V.shape} 与 A/B 数量 {(nA, nB)} 不一致。")
            if aux < 1:
                raise SystemExit(f"[归档] Ising 维度 {n_ising} 未包含辅助自旋（QUBO {n_qubo}）。")

            v_csv = arc.dir / "input" / "submitted_target_V.csv"
            with open(v_csv, "w", encoding="utf-8-sig", newline="") as f:
                f.write("A," + ",".join(B) + "\n")
                for a, row in zip(A, V):
                    f.write(a + "," + ",".join(f"{x:.17g}" for x in row) + "\n")
            readback = np.loadtxt(v_csv, delimiter=",", skiprows=1,
                                  usecols=range(1, nB + 1), dtype=np.float64, ndmin=2)
            if not np.array_equal(readback, V):
                raise SystemExit("[归档] 筛选后目标矩阵 V 回读不一致，已中止。")

            mapping = {
                "schema_version": SCHEMA_VERSION,
                "task_id": task_id,
                "input_version": exin.version,
                "input_kind": exin.kind,
                "input_matrix_sha256": exin.matrix_sha256,
                "topk": cfg.get("topk"),
                "mfactor": cfg.get("mfactor"),
                "submitted_matrix_sha256": numeric_matrix_sha256(ising_matrix),
                "submitted_matrix_shape": [n_ising, n_ising],
                "n_qubo": n_qubo,
                "n_ising": n_ising,
                "aux_spin_count": aux,
                "aux_spin_position": "last",
                "aux_spin_indices": list(range(n_qubo, n_ising)),
                "A_axis": "row",
                "B_axis": "column",
                "A": A,
                "B": B,
                "variables": (
                    [{"index": i, "kind": "A", "label": A[i]} for i in range(nA)]
                    + [{"index": nA + j, "kind": "B", "label": B[j]} for j in range(nB)]
                    + [{"index": n_qubo + k, "kind": "aux", "label": None} for k in range(aux)]
                ),
                "filtered_target_matrix": {
                    "path": "input/submitted_target_V.csv",
                    "shape": [nA, nB],
                    "file_sha256": sha256_file(v_csv),
                    "semantic_sha256": numeric_matrix_sha256(V),
                },
            }
            mapping_path = arc.dir / "input" / "submitted_mapping.json"
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
            hashes.update({
                "submitted_mapping_sha256": sha256_file(mapping_path),
                "submitted_target_V_csv_sha256": sha256_file(v_csv),
                "submitted_target_V_semantic_sha256": numeric_matrix_sha256(V),
                "submitted_matrix_sha256": numeric_matrix_sha256(ising_matrix),
            })
            cfg.update({
                "submitted_mapping_file": "input/submitted_mapping.json",
                "submitted_mapping_sha256": sha256_file(mapping_path),
                "submitted_target_V_file": "input/submitted_target_V.csv",
                "submitted_target_V_csv_sha256": sha256_file(v_csv),
                "submitted_A_count": nA,
                "submitted_B_count": nB,
                "aux_spin_count": aux,
            })
            (arc.dir / "config.json").write_text(
                json.dumps(json_safe(cfg), ensure_ascii=False, indent=2), encoding="utf-8")

        (arc.dir / "input" / "hashes.json").write_text(
            json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8")

        meta = {
            "schema_version": SCHEMA_VERSION,
            "task_id": task_id,
            "task_name": cfg.get("task_name"),
            "status": "created",
            "created_at": now_str(),
            "updated_at": now_str(),
            "input_version": exin.version,
            "input_kind": exin.kind,
            "input_matrix_sha256": exin.matrix_sha256,
            "submitted_matrix_sha256": hashes["ising_matrix_sha256"],
            "ising_shape": list(np.asarray(ising_matrix).shape),
            "sdk_matrix_hash": None,
            "mode_key": cfg.get("mode_key"),
            "mode": cfg.get("mode"),
            "topk": cfg.get("topk"),
            "mfactor": cfg.get("mfactor"),
            "samples": cfg.get("samples"),
            "quota_units": int(cfg.get("quota_units") or 0),
            "quota_counted": False,
            "device": None,
            "device_source": "pending_platform_report",
            "platform_task_id": None,
            "returned_solutions": None,
            "runtime_s": None,
            "error_stage": None,
            "error_type": None,
            "error_message": None,
            "archive_dir": str(arc.dir),
        }
        arc._write_meta(meta)
        return arc

    # ---------------------------------------------------------------- 基础读写
    def _write_meta(self, meta: dict):
        self.meta_path.write_text(json.dumps(json_safe(meta), ensure_ascii=False, indent=2),
                                  encoding="utf-8")

    def meta(self) -> dict:
        if not self.meta_path.is_file():
            raise SystemExit(f"[归档] 任务不存在：{self.task_id}")
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    def update(self, **fields) -> dict:
        meta = self.meta()
        meta.update(fields)
        meta["updated_at"] = now_str()
        self._write_meta(meta)
        return meta

    def log(self, message: str):
        line = f"[{now_str()}] {message}"
        with open(self.dir / "logs" / "run.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line)

    def append_attempt(self, stage: str, status: str, detail: str = "", **extra):
        rec = {"at": now_str(), "stage": stage, "status": status, "detail": detail}
        rec.update(json_safe(extra))
        with open(self.dir / "attempts.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---------------------------------------------------------------- 原始结果
    def save_solutions(self, solutions: np.ndarray) -> str:
        arr = np.atleast_2d(np.asarray(solutions))
        path = self.dir / "raw" / "solutions.npz"
        if path.exists():
            raise SystemExit(f"[归档] 原始解已存在，拒绝覆盖：{path}")
        np.savez(path, solutions=arr)
        fmt = "%d" if np.all(arr == np.round(arr)) else "%.10g"
        np.savetxt(self.dir / "raw" / "solutions.csv", arr, delimiter=",", fmt=fmt)
        return str(path)

    def save_platform_result(self, result) -> str:
        path = self.dir / "raw" / "platform_result.json"
        if path.exists():
            # 平台结果可能分多次拿到（先失败后成功），保留最早一份，新的加时间戳
            path = self.dir / "raw" / f"platform_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(json_safe(result), ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    def save_energy(self, solutions: np.ndarray, ising_matrix: np.ndarray):
        """按 SDK 约定 H = -sᵀJs 机械计算能量，仅作核对，不做任何科学解释。"""
        sol = np.atleast_2d(np.asarray(solutions, dtype=np.float64))
        J = np.asarray(ising_matrix, dtype=np.float64)
        H = -np.einsum("ij,ij->i", sol.dot(J), sol)
        with open(self.dir / "raw" / "solution_energy.csv", "w", encoding="utf-8") as f:
            f.write("sample,H,sum_plus_one\n")
            for i, (h, s) in enumerate(zip(H, sol)):
                f.write(f"{i},{h:.10g},{int((s > 0).sum())}\n")

    def attach_report(self, report_path: Path, device: str = None, platform_task_id: str = None,
                      hardware_ms: float = None):
        report_path = Path(report_path)
        if not report_path.is_file():
            raise SystemExit(f"[归档] 报告文件不存在：{report_path}")
        dst = self.dir / "reports" / report_path.name
        if dst.exists():
            raise SystemExit(f"[归档] 报告已存在，拒绝覆盖：{dst}")
        shutil.copy2(report_path, dst)
        fields = {"report_file": str(dst), "report_sha256": sha256_file(dst)}
        if device:
            fields.update({"device": device, "device_source": "platform_report"})
        if platform_task_id:
            fields.update({"platform_task_id": platform_task_id,
                           "platform_task_id_source": "platform_report"})
        if hardware_ms is not None:
            fields.update({"hardware_ms": float(hardware_ms),
                           "hardware_ms_source": "platform_report"})
        return self.update(**fields)

    def archive_dir_size(self) -> int:
        return sum(p.stat().st_size for p in self.dir.rglob("*") if p.is_file())
