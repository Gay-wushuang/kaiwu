# -*- coding: utf-8 -*-
"""T003 本地验证：PrecisionReducer 拆分映射、拆分一致性、G1-G4 对照。

只使用非真机后端（SA / 全空间穷举），不调用 license，不消耗配额。
输出：LOCAL_VALIDATION.json、G1_G4_LOCAL.json
"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "results/round2/qubo_refinement/EXPERIMENTS"))
import experiment_input as exin          # noqa: E402
import d_experiment as dx                # noqa: E402
import d_submit_cim as S                 # noqa: E402
import precision_reducer as PRR         # noqa: E402
import synthetic_encoding_benchmark as SB  # noqa: E402
import kaiwu as kw                       # noqa: E402
import kaiwu.preprocess as pp            # noqa: E402

OUT = Path(__file__).resolve().parent
INPUTS = {
    "B-Q2-NO2": 0.33826009024559534,
    "B-Q3-O3": 0.4296,
    "B-Q3-FO2": 0.3832,
}
PR_BASE = {"precision": 8, "target_bits": 550,
           "truncated_precision": 12, "only_feasible_solution": False}


def sa(seed, iterations=100):
    return kw.classical.SimulatedAnnealingOptimizer(
        initial_temperature=1000, alpha=0.99, cutoff_temperature=0.0001,
        iterations_per_t=iterations, rand_seed=seed)


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


def original_optimum_spins(V):
    i, j = np.unravel_index(np.argmin(V), V.shape)
    nA, nB = V.shape
    s = np.full(nA + nB + 1, -1.0)
    s[i] = 1.0
    s[nA + j] = 1.0
    s[-1] = 1.0
    return s


def truncated_scan(I, V, max_bits=20):
    n = I.shape[0]
    states = np.array(list(itertools.product([-1.0, 1.0], repeat=n - 1)))
    states = np.hstack([states, np.ones((len(states), 1))])
    mx = float(np.abs(I).max())
    rows = []
    for bits in range(8, max_bits + 1):
        s = mx / (2 ** (bits - 1) - 1)
        It = np.round(I / s) * s
        H = -np.einsum("ij,jk,ik->i", states, It, states)
        b = ((states + 1) // 2).astype(int)
        legal = (b[:, :V.shape[0]].sum(1) == 1) & (b[:, V.shape[0]:-1].sum(1) == 1)
        lmin = float(H[legal].min())
        imin = float(H[~legal].min())
        best = states[legal][H[legal] == lmin][0]
        bb = ((best + 1) // 2).astype(int)
        i = int(np.flatnonzero(bb[:V.shape[0]])[0])
        j = int(np.flatnonzero(bb[V.shape[0]:-1])[0])
        rows.append({"bits": bits, "quant_step": float(s),
                     "legal_min": lmin, "illegal_min": imin,
                     "gap": imin - lmin, "best_label": [i, j],
                     "best_V": float(V[i, j])})
    return rows


def constructed_test(I, V, meta):
    s_orig = original_optimum_spins(V)
    s_exp = np.asarray(pp.construct_split_solution(s_orig, meta["split_indices"]), float)
    H = -float(s_exp @ meta["matrix_expanded"] @ s_exp)
    feasible = bool(PRR.split_feasible(np.atleast_2d(s_exp), meta["groups"])[0])
    return {"V_opt": float(V.min()), "constructed_feasible": feasible,
            "constructed_H": H,
            "constructed_restore": pp.restore_split_solution(s_exp, meta["split_indices"]).tolist()}


def local_case(ver, mfactor, tp, seeds=(0, 1, 2, 3, 4)):
    e = exin.load(ver)
    p = dx.build_problem(e, topk=8, mfactor=mfactor)
    q = dx.build_problem(e, topk=8, mfactor=mfactor,
                         precision_method="precision_reducer",
                         pr_params={**PR_BASE, "truncated_precision": tp})
    V, I = p["V"], p["I"]
    meta = PRR.expand_ising(I, {**PR_BASE, "truncated_precision": tp})
    ct = constructed_test(I, V, meta)
    rows = []
    for seed in range(len(seeds)):
        rec = RecSA(initial_temperature=1000, alpha=0.99, cutoff_temperature=0.0001,
                   iterations_per_t=100, rand_seed=seed)
        t0 = time.perf_counter()
        pr = pp.PrecisionReducer(rec, **{**PR_BASE, "truncated_precision": tp})
        sol = np.atleast_2d(pr.solve(I))
        elapsed = time.perf_counter() - t0
        feas = PRR.split_feasible(rec.E, meta["groups"])
        H = -np.einsum("ij,jk,ik->i", rec.E, meta["matrix_expanded"], rec.E)
        vals = decode(sol, V)
        restored, ok = PRR.restore_feasible(rec.E, meta["split_indices"])
        feas_vals = decode(restored[ok], V)
        rows.append({
            "seed": seed, "n_expanded_samples": int(rec.E.shape[0]),
            "split_feasible": int(feas.sum()),
            "best_feasible_H": float(H[feas].min()) if feas.any() else None,
            "best_sampled_H": float(H.min()),
            "constructed_H_minus_sampled_best": float(ct["constructed_H"] - H.min()),
            "returns": int(sol.shape[0]), "legal": len(vals),
            "best_V": float(min(vals)) if vals else None,
            "feasible_legal": len(feas_vals),
            "feasible_best_V": float(min(feas_vals)) if feas_vals else None,
            "runtime_s": elapsed,
        })
    return {"input": ver, "mfactor": mfactor, "tp": tp,
            "n_original": q["n_ising_original"], "n_expanded": q["n_ising"],
            "extra_spins": q["split_extra_spins"], "mapping_status": q["mapping_status"],
            "expanded_sha256": q["matrix_sha256"],
            "split_groups": [list(map(int, g)) for g in q["split_groups"]],
            "constructed": ct, "runs": rows,
            "direct8": {"n_ising": p["n_ising"], "sha256": p["matrix_sha256"],
                        "resol_raw": p["resol_raw"], "resol_adj": p["resol_adj"]}}


def g1_g4(ver, mfactor):
    e = exin.load(ver)
    p = dx.build_problem(e, topk=8, mfactor=mfactor)
    q = dx.build_problem(e, topk=8, mfactor=mfactor,
                         precision_method="precision_reducer", pr_params=PR_BASE)
    V, I = p["V"], p["I"]
    meta = PRR.expand_ising(I, PR_BASE)
    out = {"input": ver, "V_min": float(V.min()), "G1_G2": {}, "G3_G4": {}}
    for seed in range(5):
        sol = np.atleast_2d(sa(seed).solve(p["adj"]))
        vals = decode(sol, V)
        out["G1_G2"].setdefault("direct8", []).append({
            "seed": seed, "rows": int(sol.shape[0]), "legal": len(vals),
            "best_V": float(min(vals)) if vals else None,
            "hit_original": bool(vals and min(vals) <= 0.0)})
    for seed in range(5):
        rec = RecSA(initial_temperature=1000, alpha=0.99, cutoff_temperature=0.0001,
                   iterations_per_t=100, rand_seed=seed)
        pr = pp.PrecisionReducer(rec, **PR_BASE)
        sol = np.atleast_2d(pr.solve(I))
        feas = PRR.split_feasible(rec.E, meta["groups"])
        vals = decode(sol, V)
        restored, ok = PRR.restore_feasible(rec.E, meta["split_indices"])
        feas_vals = decode(restored[ok], V)
        out["G3_G4"].setdefault("precision_reducer", []).append({
            "seed": seed, "rows": int(sol.shape[0]), "split_feasible": int(feas.sum()),
            "legal": len(vals), "best_V": float(min(vals)) if vals else None,
            "hit_original": bool(vals and min(vals) <= 0.0),
            "feasible_legal": len(feas_vals),
            "feasible_best_V": float(min(feas_vals)) if feas_vals else None,
            "feasible_hit_original": bool(feas_vals and min(feas_vals) <= 0.0)})
    out["expanded"] = {"n_original": q["n_ising_original"], "n_expanded": q["n_ising"],
                       "extra_spins": q["split_extra_spins"],
                       "mapping_status": q["mapping_status"],
                       "matrix_sha256": q["matrix_sha256"]}
    return out


t0 = time.perf_counter()
payload = {"schema_version": 1,
           "scope": "local SA / exhaustive validation; no hardware, no quota",
           "pr_base": PR_BASE, "cases": [], "truncated_scan": {},
           "small_case_bruteforce": None, "g1_g4": []}

for ver, mf in INPUTS.items():
    for tp in (10, 12, 14, 16):
        payload["cases"].append(local_case(ver, mf, tp))

# Q2 lowM：截断位宽全空间枚举（辅助位固定 +1）
e = exin.load("B-Q2-NO2")
p = dx.build_problem(e, topk=8, mfactor=INPUTS["B-Q2-NO2"])
payload["truncated_scan"]["B-Q2-NO2_lowM"] = truncated_scan(p["I"], p["V"])
payload["truncated_scan"]["V_min"] = float(p["V"].min())

# 小规模教学案例：拆分后全空间枚举（2^17），验证拆分等价
V = np.array([[0.0, 0.0], [1.0, 0.5]])
M = float(max(2 * (V.max() - V.min()), 1) + 15)
Q, off = SB.build_onehot(V, M)
I, _ = S.to_ising(Q)
meta = PRR.expand_ising(I, {"precision": 4, "target_bits": None,
                            "truncated_precision": 20, "only_feasible_solution": False})
pr = pp.PrecisionReducer(kw.classical.BruteForceOptimizer(), precision=4)
restored = np.atleast_2d(pr.solve(I))
labels = decode(restored, V)
payload["small_case_bruteforce"] = {
    "V": V.tolist(), "M": M, "n_original": I.shape[0],
    "n_expanded": meta["n_expanded"], "mapping_status": meta["mapping_status"],
    "split_indices": (None if meta["split_indices"] is None
                      else [int(v) for v in meta["split_indices"]]),
    "bruteforce_restored_labels": labels,
    "bruteforce_best_V": float(min(labels)) if labels else None,
    "original_optimal_V": 0.0,
    "legal_set_equal_or_subset": bool(labels) and min(labels) <= 1e-12,
}

for ver, mf in INPUTS.items():
    payload["g1_g4"].append(g1_g4(ver, mf))

payload["runtime_s"] = time.perf_counter() - t0
(OUT / "LOCAL_VALIDATION.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "G1_G4_LOCAL.json").write_text(
    json.dumps(payload["g1_g4"], ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "small_case": payload["small_case_bruteforce"],
    "q2_lowM_trunc": payload["truncated_scan"]["B-Q2-NO2_lowM"],
    "g1_g4": payload["g1_g4"],
}, ensure_ascii=False, indent=1)[:6000])
