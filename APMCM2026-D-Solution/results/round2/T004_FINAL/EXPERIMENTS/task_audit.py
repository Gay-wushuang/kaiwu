# -*- coding: utf-8 -*-
"""T004-04：全部已完成真机任务的统一口径复算（不提交、不消耗配额）。

口径：
  - 返回样本数、原始 one-hot 合法率、拆分一致率（仅 PR）、两者同时满足率（仅 PR）；
  - 严格有效的原始最优命中 = 合法（PR 还需拆分一致）且 V̂ 等于该输入全矩阵原始最优；
  - direct8 的拆分指标为 N/A（None），不填 0。
输出：task_audit.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
CODE = ROOT / "code"
sys.path.insert(0, str(CODE))

import precision_reducer as PRR                 # noqa: E402
from experiment_input import matrix_sha256, numeric_matrix_sha256  # noqa: E402

TASKS = ROOT / "experiments" / "tasks"
OUT = Path(__file__).resolve().parent / "task_audit.json"


def load_matrix(path):
    df = pd.read_csv(path, index_col=0)
    return [str(x) for x in df.index], [str(x) for x in df.columns], df.to_numpy(float)


def decode_rows(rows, A, B, V):
    """按相对自旋 x_i=(s_i*s_aux+1)/2 解码；末位必须是原始辅助自旋。"""
    nA, nB = len(A), len(B)
    out = []
    for k, s in enumerate(np.atleast_2d(rows)):
        if not np.all(np.isfinite(s)):
            out.append(dict(sample=k, legal=False, reason="restore_conflict"))
            continue
        try:
            bits = PRR.logical_bits_from_spins(s)[0][: nA + nB]
        except ValueError:
            out.append(dict(sample=k, legal=False, reason="decode_error"))
            continue
        ia = [i for i in range(nA) if bits[i] == 1]
        ib = [i - nA for i in range(nA, nA + nB) if bits[i] == 1]
        if len(ia) == 1 and len(ib) == 1:
            out.append(dict(sample=k, legal=True, i=int(ia[0]), j=int(ib[0]),
                            A=A[ia[0]], B=B[ib[0]], V=float(V[ia[0], ib[0]])))
        else:
            out.append(dict(sample=k, legal=False, reason="onehot_violation"))
    return out


def audit(task_dir: Path):
    cfg = json.loads((task_dir / "config.json").read_text(encoding="utf-8-sig"))
    task = json.loads((task_dir / "task.json").read_text(encoding="utf-8-sig"))
    A_in, B_in, V_in = load_matrix(task_dir / "input" / "matrix.csv")
    subm = json.loads((task_dir / "input" / "submitted_mapping.json").read_text(encoding="utf-8-sig"))
    A, B = subm["A"], subm["B"]
    V = pd.read_csv(task_dir / "input" / "submitted_target_V.csv", index_col=0).to_numpy(float)
    is_pr = cfg.get("precision_method") == "precision_reducer"
    if is_pr:
        # PR 任务以 npz 为准：CSV 往返会把 +0.0 写成 -0.0，字节哈希改变
        adj = np.load(task_dir / "input" / "ising_matrix_expanded.npz")["matrix"].astype(float)
    else:
        adj = pd.read_csv(task_dir / "input" / "ising_matrix.csv", header=None).to_numpy(float)
    sol = np.load(task_dir / "raw" / "solutions.npz")["solutions"]
    energy = pd.read_csv(task_dir / "raw" / "solution_energy.csv")
    vmin_full = float(V_in.min())
    vmin_sub = float(V.min())
    raw_pairs = {(A_in[i], B_in[j]) for i, j in np.argwhere(V_in <= vmin_full + 1e-12)}
    sub_pairs = {(A[i], B[j]) for i, j in np.argwhere(V <= vmin_sub + 1e-12)}

    res = dict(
        task_id=task["task_id"], task_name=task["task_name"],
        input_version=cfg["input_version"], precision_method=cfg.get("precision_method"),
        topk=cfg.get("topk"), mfactor=cfg.get("mfactor"),
        n_qubo=cfg.get("n_qubo"), n_ising=cfg.get("n_ising"),
        n_ising_original=cfg.get("n_ising_original"), split_extra_spins=cfg.get("split_extra_spins"),
        M=cfg.get("M"), resol_raw=cfg.get("resol_raw"), resol_adj=cfg.get("resol_adj"),
        device=task.get("device"), platform_task_id=task.get("platform_task_id"),
        hardware_ms=task.get("hardware_ms"), runtime_s=task.get("runtime_s"),
        quota_counted=task.get("quota_counted"),
        input_matrix_sha256=matrix_sha256(A_in, B_in, V_in),
        archived_input_matrix_sha256=cfg.get("input_matrix_sha256"),
        submitted_matrix_sha256=numeric_matrix_sha256(adj),
        archived_submitted_matrix_sha256=cfg.get("submitted_matrix_sha256"),
        returned=int(sol.shape[0]), vmin_full=vmin_full, vmin_sub=vmin_sub,
        full_argmin=sorted(raw_pairs), sub_argmin=sorted(sub_pairs),
    )

    if is_pr:
        exp = np.load(task_dir / "raw" / "solutions_expanded.npz")["solutions"]
        H_rows = [float(-s.astype(float) @ adj @ s.astype(float)) for s in exp]
        energy_exp = pd.read_csv(task_dir / "raw" / "solution_energy_expanded.csv")
        res["H_matches_archived"] = bool(np.allclose(H_rows, energy_exp.H.to_numpy(float),
                                                     atol=1e-6, rtol=0))
    else:
        H_rows = [float(-s.astype(float) @ adj @ s.astype(float)) for s in sol]
        res["H_matches_archived"] = bool(np.allclose(H_rows, energy.H.to_numpy(float),
                                                     atol=1e-6, rtol=0))

    if is_pr:
        sm = json.loads((task_dir / "input" / "split_mapping.json").read_text(encoding="utf-8-sig"))
        restored, feasible = PRR.restore_feasible(exp, sm["split_indices"])
        rows = decode_rows(sol, A, B, V)          # PrecisionReducer 包装器恢复结果
        rows_ind = decode_rows(restored, A, B, V)  # 独立 split 一致子空间恢复
        for r, ri, f in zip(rows, rows_ind, feasible):
            r["split_feasible"] = bool(f)
            r["strict_valid"] = bool(f and r.get("legal"))
            r["hit_raw_opt"] = bool(r["strict_valid"] and (r.get("A"), r.get("B")) in raw_pairs)
            ri["split_feasible"] = bool(f)
            ri["strict_valid"] = bool(f and ri.get("legal"))
            ri["hit_raw_opt"] = bool(ri["strict_valid"] and (ri.get("A"), ri.get("B")) in raw_pairs)
        legal_w = sum(r.get("legal", False) for r in rows)
        res.update(dict(
            returned_expanded=int(exp.shape[0]),
            split_feasible=int(feasible.sum()),
            split_feasible_rate=float(feasible.sum() / len(feasible)),
            legal=int(legal_w),
            legal_rate=float(legal_w / len(rows)),
            legal_independent=int(sum(r.get("legal", False) for r in rows_ind)),
            both=int(sum(r.get("strict_valid", False) for r in rows)),
            both_rate=float(sum(r.get("strict_valid", False) for r in rows) / len(rows)),
            strict_hit=int(sum(r.get("hit_raw_opt", False) for r in rows)),
            best_legal_V=min([r["V"] for r in rows if r.get("legal")], default=None),
            best_strict_V=min([r["V"] for r in rows if r.get("strict_valid")], default=None),
            rows=rows, rows_independent=rows_ind,
        ))
    else:
        rows = decode_rows(sol, A, B, V)
        for r in rows:
            if r.get("legal"):
                r["hit_raw_opt"] = bool((r.get("A"), r.get("B")) in raw_pairs)
                r["hit_sub_opt"] = bool((r.get("A"), r.get("B")) in sub_pairs)
        legal = sum(r.get("legal", False) for r in rows)
        # 8bit 适配后的合法域最优集合（逻辑规范代表 aux=+1）
        nA, nB = len(A), len(B)
        leg = []
        for i in range(nA):
            for j in range(nB):
                s = -np.ones(nA + nB + 1)
                s[i] = 1
                s[nA + j] = 1
                s[-1] = 1
                leg.append((i, j, float(V[i, j]), float(-s @ adj @ s)))
        hmin = min(r[3] for r in leg)
        qset = {(A[i], B[j]) for i, j, _, h in leg if abs(h - hmin) < 1e-9}
        qret = len(qset & raw_pairs) / max(len(raw_pairs), 1)
        res.update(dict(
            split_feasible=None, split_feasible_rate=None,
            legal=int(legal), legal_rate=float(legal / len(rows)),
            both=None, both_rate=None,
            strict_hit=int(sum(r.get("hit_raw_opt", False) for r in rows)),
            best_legal_V=min([r["V"] for r in rows if r.get("legal")], default=None),
            best_strict_V=None,
            quantized_legal_min_H=float(hmin),
            quantized_legal_set=sorted((a, b, float(V[A.index(a), B.index(b)])) for a, b in qset),
            quantized_retention=float(qret),
            quantized_extra=int(len(qset - raw_pairs)),
            rows=rows,
        ))
    return res


def main():
    out = []
    for d in sorted(TASKS.iterdir()):
        if not d.is_dir():
            continue
        tj = d / "task.json"
        if not tj.is_file():
            continue
        task = json.loads(tj.read_text(encoding="utf-8-sig"))
        if task.get("status") != "completed":
            continue
        out.append(audit(d))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    cols = ["task_name", "input_version", "precision_method", "topk", "n_ising",
            "device", "returned", "legal", "split_feasible", "both", "strict_hit",
            "best_legal_V", "best_strict_V", "hardware_ms", "runtime_s",
            "H_matches_archived", "input_matrix_sha256", "submitted_matrix_sha256"]
    print(pd.DataFrame(out)[cols].to_string(index=False))
    for r in out:
        print(f"\n{r['task_name']}: vmin_full={r['vmin_full']} argmin={r['full_argmin']}")
        for row in r["rows"]:
            print("  ", row)


if __name__ == "__main__":
    main()
