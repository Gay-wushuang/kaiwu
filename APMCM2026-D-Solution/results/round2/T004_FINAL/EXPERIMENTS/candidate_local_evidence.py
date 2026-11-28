# -*- coding: utf-8 -*-
"""三个真机候选的本地证据：量化合法最优集合/原始最优保留；不提交。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))

import experiment_input as exin          # noqa: E402
import d_experiment as dx                # noqa: E402

OUT = Path(__file__).resolve().parent / "CANDIDATE_LOCAL_EVIDENCE.json"


def legal_set(V, adj):
    nA, nB = V.shape
    best = None
    rows = []
    for i in range(nA):
        for j in range(nB):
            s = -np.ones(nA + nB + 1)
            s[i] = 1
            s[nA + j] = 1
            s[-1] = 1
            h1 = float(-s @ adj @ s)
            s[-1] = -1
            h2 = float(-s @ adj @ s)
            h = min(h1, h2)
            rows.append((i, j, float(V[i, j]), h))
            best = h if best is None else min(best, h)
    qset = [(i, j) for i, j, _, h in rows if abs(h - best) < 1e-9]
    vmin = float(V.min())
    raw = [(i, j) for i, j, v, _ in rows if abs(v - vmin) < 1e-12]
    hit = len(set(qset) & set(raw))
    return dict(min_H=best, qset=[(i, j, float(V[i, j])) for i, j in qset],
                raw=[(i, j, float(V[i, j])) for i, j in raw],
                retention=hit / max(len(raw), 1),
                quantized_extra=len(set(qset) - set(raw)))


def route(ver, mfactor, method, topk=13, pr_params=None):
    e = exin.load(ver)
    p = dx.build_problem(e, topk=topk, mfactor=mfactor, precision_method=method,
                         pr_params=pr_params)
    out = dict(input=ver, mfactor=mfactor, method=method,
               n_qubo=p["n_qubo"], n_ising_original=p["n_ising_original"],
               n_submitted=p["n_ising"], extra=p["split_extra_spins"],
               M=p["M"], matrix_sha256=p["matrix_sha256"],
               A=p["A"], B=p["B"])
    if method == "direct_8bit":
        out.update(legal_set(p["V"], p["adj"]))
    else:
        out.update(mapping_status=p["mapping_status"],
                   constructed_feasible=None,
                   note="扩展空间未做全空间枚举；仅候选 dry-run 与映射核验")
    return out


def main():
    pr14 = {"precision": 8, "target_bits": 550, "truncated_precision": 14,
            "only_feasible_solution": False}
    out = {
        "Q3_O3_lowM_direct8": route("B-Q3-O3", 0.4296, "direct_8bit"),
        "Q3_FO2_lowM_direct8": route("B-Q3-FO2", 0.3832, "direct_8bit"),
        "G3_Q2_M0_PR_tp14": route("B-Q2-NO2", 1.0, "precision_reducer", 8, pr14),
    }
    for k, v in out.items():
        if "A" in v:
            v["A"] = v["A"]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, v in out.items():
        print("=== ", k)
        for f in ("n_submitted", "extra", "M", "matrix_sha256", "min_H",
                  "retention", "extra", "qset", "raw"):
            if f in v:
                print(f"  {f}: {v[f]}")


if __name__ == "__main__":
    main()
