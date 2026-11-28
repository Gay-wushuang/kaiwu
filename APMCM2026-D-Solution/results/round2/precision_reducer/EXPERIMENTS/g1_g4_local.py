# -*- coding: utf-8 -*-
"""T003-05：G1-G4 四组本地对照（SA，非真机）。

G1：M0 + direct8；G2：lowM + direct8；
G3：M0 + PrecisionReducer；G4：lowM + PrecisionReducer。
输出：G1_G4_LOCAL.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))
import experiment_input as exin          # noqa: E402
import d_experiment as dx                # noqa: E402
import precision_reducer as PRR         # noqa: E402
import kaiwu as kw                       # noqa: E402
import kaiwu.preprocess as pp            # noqa: E402

OUT = Path(__file__).resolve().parent
MF = {"B-Q2-NO2": 0.33826009024559534, "B-Q3-O3": 0.4296, "B-Q3-FO2": 0.3832}
PR = {"precision": 8, "target_bits": 550,
      "truncated_precision": 12, "only_feasible_solution": False}


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
        b = PRR.logical_bits_from_spins(s)[0][:nA + nB]
        ia = [i for i in range(nA) if b[i] == 1]
        ib = [i - nA for i in range(nA, nA + nB) if b[i] == 1]
        if len(ia) == 1 and len(ib) == 1:
            vals.append(float(V[ia[0], ib[0]]))
    return vals


def run_direct(p, seeds=5):
    rows = []
    for seed in range(seeds):
        sol = np.atleast_2d(kw.classical.SimulatedAnnealingOptimizer(
            initial_temperature=1000, alpha=0.99, cutoff_temperature=0.0001,
            iterations_per_t=100, rand_seed=seed).solve(p["adj"]))
        vals = decode(sol, p["V"])
        rows.append({"seed": seed, "rows": int(sol.shape[0]), "legal": len(vals),
                     "best_V": float(min(vals)) if vals else None,
                     "hit_original": bool(vals and min(vals) <= 0.0)})
    return rows


def run_pr(p, meta, seeds=5):
    rows = []
    for seed in range(seeds):
        rec = RecSA(initial_temperature=1000, alpha=0.99, cutoff_temperature=0.0001,
                    iterations_per_t=100, rand_seed=seed)
        sol = np.atleast_2d(pp.PrecisionReducer(rec, **p["precision_params"]).solve(p["I"]))
        feas = PRR.split_feasible(rec.E, meta["groups"])
        restored, ok = PRR.restore_feasible(rec.E, meta["split_indices"])
        feas_vals = decode(restored[ok], p["V"])
        vals = decode(sol, p["V"])
        rows.append({"seed": seed, "rows": int(sol.shape[0]),
                     "split_feasible": int(feas.sum()), "legal": len(vals),
                     "best_V": float(min(vals)) if vals else None,
                     "hit_original": bool(vals and min(vals) <= 0.0),
                     "feasible_legal": len(feas_vals),
                     "feasible_best_V": float(min(feas_vals)) if feas_vals else None,
                     "feasible_hit_original": bool(feas_vals and min(feas_vals) <= 0.0)})
    return rows


t0 = time.perf_counter()
out = {"schema_version": 1, "scope": "local SA; no hardware, no quota",
       "pr_params": PR, "inputs": []}
for ver in MF:
    e = exin.load(ver)
    entry = {"input": ver, "V_min": None, "groups": {}}
    for name, mf in (("M0", 1.0), ("lowM", MF[ver])):
        p = dx.build_problem(e, topk=8, mfactor=mf)
        q = dx.build_problem(e, topk=8, mfactor=mf,
                             precision_method="precision_reducer", pr_params=PR)
        meta = PRR.expand_ising(p["I"], PR)
        entry["V_min"] = float(p["V"].min())
        entry["groups"][name] = {
            "mfactor": mf, "direct8": {"n_ising": p["n_ising"],
                                       "sha256": p["matrix_sha256"],
                                       "runs": run_direct(p)},
            "precision_reducer": {
                "n_original": q["n_ising_original"], "n_expanded": q["n_ising"],
                "extra_spins": q["split_extra_spins"],
                "mapping_status": q["mapping_status"],
                "sha256": q["matrix_sha256"], "runs": run_pr(q, meta)},
        }
    out["inputs"].append(entry)
out["runtime_s"] = time.perf_counter() - t0
(OUT / "G1_G4_LOCAL.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
for e in out["inputs"]:
    print("=" * 20, e["input"])
    for name, g in e["groups"].items():
        d8, pr = g["direct8"], g["precision_reducer"]
        print(f"  {name}: direct8 best {[r['best_V'] for r in d8['runs']]} legal {[r['legal'] for r in d8['runs']]}")
        print(f"        PR N={pr['n_expanded']} feas {[r['split_feasible'] for r in pr['runs']]} "
              f"feasible best {[r['feasible_best_V'] for r in pr['runs']]}")
