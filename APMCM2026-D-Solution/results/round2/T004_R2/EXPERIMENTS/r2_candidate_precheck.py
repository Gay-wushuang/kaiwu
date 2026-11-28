# -*- coding: utf-8 -*-
"""T004-R2 候选本地预检：规模、哈希、原始/量化最优、PR 构造态可行性。不提交。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))

import experiment_input as exin          # noqa: E402
import d_experiment as dx                # noqa: E402
import precision_reducer as PRR         # noqa: E402
import kaiwu.preprocess as pp            # noqa: E402

OUT = Path(__file__).resolve().parent / "R2_CANDIDATE_PRECHECK.json"


def original_optimum_spins(V):
    i, j = np.unravel_index(np.argmin(V), V.shape)
    nA, nB = V.shape
    s = np.full(nA + nB + 1, -1.0)
    s[i] = 1.0
    s[nA + j] = 1.0
    s[-1] = 1.0
    return s, i, j


def qset_direct8(V, adj):
    nA, nB = V.shape
    rows = []
    for i in range(nA):
        for j in range(nB):
            s = -np.ones(nA + nB + 1)
            s[i] = 1
            s[nA + j] = 1
            s[-1] = 1
            rows.append((i, j, float(V[i, j]), float(-s @ adj @ s)))
    hmin = min(r[3] for r in rows)
    q = {(i, j) for i, j, _, h in rows if abs(h - hmin) < 1e-9}
    vmin = float(V.min())
    raw = {(i, j) for i, j, v, _ in rows if abs(v - vmin) < 1e-12}
    return dict(min_H=hmin, qset=sorted((i, j, float(V[i, j])) for i, j in q),
                raw=sorted((i, j, float(V[i, j])) for i, j in raw),
                retention=len(q & raw) / max(len(raw), 1),
                quantized_extra=len(q - raw))


def main():
    specs = [
        ("Q3_O3_lowM_direct8", "B-Q3-O3", 13, 0.4296, "direct_8bit", None),
        ("Q3_FO2_lowM_direct8", "B-Q3-FO2", 13, 0.3832, "direct_8bit", None),
        ("G3_Q2_M0_PR_tp14", "B-Q2-NO2", 8, 1.0, "precision_reducer",
         {"precision": 8, "target_bits": 550, "truncated_precision": 14,
          "only_feasible_solution": False}),
        ("Q3_O3_lowM_PR_tp14", "B-Q3-O3", 13, 0.4296, "precision_reducer",
         {"precision": 8, "target_bits": 550, "truncated_precision": 14,
          "only_feasible_solution": False}),
        ("Q3_FO2_lowM_PR_tp14", "B-Q3-FO2", 13, 0.3832, "precision_reducer",
         {"precision": 8, "target_bits": 550, "truncated_precision": 14,
          "only_feasible_solution": False}),
    ]
    out = {}
    for name, ver, topk, mf, method, params in specs:
        e = exin.load(ver)
        p = dx.build_problem(e, topk=topk, mfactor=mf, precision_method=method,
                             pr_params=params)
        s_opt, i, j = original_optimum_spins(p["V"])
        rec = dict(input=ver, topk=topk, mfactor=mf, method=method,
                   n_qubo=p["n_qubo"], n_ising_original=p["n_ising_original"],
                   n_submitted=p["n_ising"], extra=p["split_extra_spins"],
                   M=p["M"], matrix_sha256=p["matrix_sha256"],
                   raw_opt=(i, j, float(p["V"][i, j])),
                   raw_argmin_count=int((p["V"] <= p["V"].min() + 1e-12).sum()),
                   A=p["A"], B=p["B"])
        if method == "direct_8bit":
            rec.update(qset_direct8(p["V"], p["adj"]))
        else:
            meta = PRR.expand_ising(p["I"], params)
            s_exp = np.asarray(pp.construct_split_solution(s_opt, meta["split_indices"]), float)
            H = -float(s_exp @ meta["matrix_expanded"] @ s_exp)
            feasible = bool(PRR.split_feasible(np.atleast_2d(s_exp), meta["groups"])[0])
            restored = pp.restore_split_solution(s_exp, meta["split_indices"])
            rec.update(mapping_status=meta["mapping_status"],
                       constructed_feasible=feasible, constructed_H=H,
                       constructed_restore=[int(v) for v in np.sign(restored)],
                       constructed_restore_logical_bits=
                       PRR.logical_bits_from_spins(restored)[0].tolist())
        out[name] = rec
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for k, v in out.items():
        print("===", k)
        for f in ("input", "topk", "mfactor", "method", "n_submitted", "extra", "M",
                  "matrix_sha256", "raw_opt", "qset", "raw", "retention", "extra",
                  "mapping_status", "constructed_feasible", "constructed_H"):
            if f in v:
                print(f"  {f}: {v[f]}")


if __name__ == "__main__":
    main()
