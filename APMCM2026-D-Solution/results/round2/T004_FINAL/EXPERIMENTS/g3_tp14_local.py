# -*- coding: utf-8 -*-
"""G3（M0 + PrecisionReducer tp14）本地 SA 对照，补齐 2×2 缺格；不提交真机。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))

import experiment_input as exin          # noqa: E402
import d_experiment as dx                # noqa: E402
import precision_reducer as PRR          # noqa: E402
import kaiwu as kw                       # noqa: E402
import kaiwu.preprocess as pp            # noqa: E402

OUT = Path(__file__).resolve().parent / "G3_TP14_LOCAL.json"
PR = {"precision": 8, "target_bits": 550, "truncated_precision": 14,
      "only_feasible_solution": False}


class RecSA(kw.classical.SimulatedAnnealingOptimizer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.E = None

    def solve(self, *args, **kwargs):
        self.E = np.atleast_2d(np.array(super().solve(*args, **kwargs), copy=True))
        return self.E


def decode(solutions, V):
    nA, nB = V.shape
    vals = []
    for s in np.atleast_2d(solutions):
        b = ((s + 1) // 2).astype(int)[:nA + nB]
        ia = [i for i in range(nA) if b[i] == 1]
        ib = [i - nA for i in range(nA, nA + nB) if b[i] == 1]
        vals.append(float(V[ia[0], ib[0]]) if len(ia) == 1 and len(ib) == 1 else None)
    return vals


def main():
    e = exin.load("B-Q2-NO2")
    p = dx.build_problem(e, topk=8, mfactor=1.0,
                         precision_method="precision_reducer", pr_params=PR)
    meta = PRR.expand_ising(p["I"], PR)
    rows = []
    for seed in range(5):
        rec = RecSA(initial_temperature=1000, alpha=0.99, cutoff_temperature=0.0001,
                    iterations_per_t=100, rand_seed=seed)
        sol = np.atleast_2d(pp.PrecisionReducer(rec, **PR).solve(p["I"]))
        feas = PRR.split_feasible(rec.E, meta["groups"])
        restored, ok = PRR.restore_feasible(rec.E, meta["split_indices"])
        vals = decode(restored[ok], p["V"]) if np.any(ok) else []
        vals = [v for v in vals if v is not None]
        rows.append(dict(seed=seed, rows=int(sol.shape[0]),
                         split_feasible=int(feas.sum()),
                         feasible_legal=len(vals),
                         feasible_best_V=float(min(vals)) if vals else None,
                         feasible_hit_original=bool(vals and min(vals) <= 0.0)))
    out = dict(input="B-Q2-NO2", route="G3_M0_PR_tp14", params=PR,
               n_original=p["n_ising_original"], n_expanded=p["n_ising"],
               extra_spins=p["split_extra_spins"], mapping_status=p["mapping_status"],
               matrix_sha256=p["matrix_sha256"], runs=rows)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
