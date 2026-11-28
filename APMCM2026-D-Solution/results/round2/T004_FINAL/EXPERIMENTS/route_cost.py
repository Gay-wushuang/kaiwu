# -*- coding: utf-8 -*-
"""T004-04 成本层：G1–G4 本地构造/精度适配耗时（不提交、不消耗配额）。"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))

import d_submit_cim as S                 # noqa: E402
import precision_reducer as PRR          # noqa: E402
import kaiwu.preprocess as pp            # noqa: E402

PRED_B = ROOT / "results" / "reproduction_20261127" / "predictions"
OUT = Path(__file__).resolve().parent / "route_cost.json"
MF = {"B-Q2-NO2": 0.33826009024559534, "B-Q3-O3": 0.4296, "B-Q3-FO2": 0.3832}
REPEATS = 5


def load_q3(x):
    import pandas as pd
    d = pd.read_csv(PRED_B / "pool_q3_phys.csv")
    d = d[d.X.astype(str) == x]
    Vdf = d.pivot_table(index="A", columns="B", values="V_hat", aggfunc="first")
    return [str(v) for v in Vdf.index], [str(v) for v in Vdf.columns], Vdf.to_numpy(float)


def load_q2():
    import pandas as pd
    d = pd.read_csv(PRED_B / "pool_q2_phys.csv")
    Vdf = d.pivot_table(index="A", columns="B", values="V_hat", aggfunc="first")
    return [str(v) for v in Vdf.index], [str(v) for v in Vdf.columns], Vdf.to_numpy(float)


def time_route(A, B, V, topk, mfactor, method, pr_params=None):
    rows = []
    for _ in range(REPEATS):
        ia = np.argsort(V.min(1))[:topk]
        ib = np.argsort(V.min(0))[:topk]
        Vs = V[np.ix_(ia, ib)]
        t0 = time.perf_counter()
        Q, offset, M0 = S.build_qubo(Vs)
        M = M0 * mfactor
        if mfactor != 1.0:
            Q, offset, M = S.build_qubo(Vs, M=M)
        I, bias = S.to_ising(Q)
        t1 = time.perf_counter()
        if method == "direct8":
            adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
            extra = 0
        else:
            exp = PRR.expand_ising(I, pr_params)
            adj = np.asarray(exp["matrix_submitted"], dtype=float)
            extra = int(adj.shape[0] - I.shape[0])
        t2 = time.perf_counter()
        rows.append(dict(build_s=t1 - t0, adapt_s=t2 - t1, total_s=t2 - t0,
                         n_qubo=int(Q.shape[0]), n_original=int(I.shape[0]),
                         n_submitted=int(adj.shape[0]), extra=extra, M=float(M),
                         sha256=_sha(adj)))
    med = lambda k: float(statistics.median(r[k] for r in rows))
    return dict(method=method, topk=topk, mfactor=mfactor,
                pr_params=pr_params, repeats=REPEATS,
                build_s_median=med("build_s"), adapt_s_median=med("adapt_s"),
                total_s_median=med("total_s"), build_s_min=min(r["build_s"] for r in rows),
                adapt_s_min=min(r["adapt_s"] for r in rows),
                total_s_min=min(r["total_s"] for r in rows),
                n_qubo=rows[0]["n_qubo"], n_original=rows[0]["n_original"],
                n_submitted=rows[0]["n_submitted"], extra=rows[0]["extra"],
                M=rows[0]["M"], sha256=rows[0]["sha256"])


def _sha(mat):
    from experiment_input import numeric_matrix_sha256
    return numeric_matrix_sha256(mat)


def main():
    A, B, V = load_q2()
    pr12 = {"precision": 8, "target_bits": 550, "truncated_precision": 12,
            "only_feasible_solution": False}
    pr14 = dict(pr12, truncated_precision=14)
    out = dict(
        baseline="B", repeats=REPEATS,
        Q2=dict(
            G1_M0_direct8=time_route(A, B, V, 8, 1.0, "direct8"),
            G2_lowM_direct8=time_route(A, B, V, 8, MF["B-Q2-NO2"], "direct8"),
            G3_M0_PR_tp12=time_route(A, B, V, 8, 1.0, "precision_reducer", pr12),
            G3_M0_PR_tp14=time_route(A, B, V, 8, 1.0, "precision_reducer", pr14),
            G4_lowM_PR_tp12=time_route(A, B, V, 8, MF["B-Q2-NO2"], "precision_reducer", pr12),
            G4_lowM_PR_tp14=time_route(A, B, V, 8, MF["B-Q2-NO2"], "precision_reducer", pr14),
        ),
        Q3={},
    )
    for x in ("O3", "FO2"):
        Ax, Bx, Vx = load_q3(x)
        out["Q3"][x] = dict(
            M0_direct8_topk13=time_route(Ax, Bx, Vx, 13, 1.0, "direct8"),
            lowM_direct8_topk13=time_route(Ax, Bx, Vx, 13, MF[f"B-Q3-{x}"], "direct8"),
            lowM_PR_tp14_topk13=time_route(Ax, Bx, Vx, 13, MF[f"B-Q3-{x}"],
                                          "precision_reducer", pr14),
        )
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for grp in ("Q2",):
        print("=" * 20, grp)
        for k, v in out[grp].items():
            print(f"{k:24s} spins {v['n_original']:4d}->{v['n_submitted']:4d} "
                  f"M={v['M']:9.3f} build={v['build_s_median']*1000:7.2f}ms "
                  f"adapt={v['adapt_s_median']*1000:7.2f}ms total={v['total_s_median']*1000:7.2f}ms")
    for x in ("O3", "FO2"):
        print("=" * 20, "Q3", x)
        for k, v in out["Q3"][x].items():
            print(f"{k:28s} spins {v['n_original']:4d}->{v['n_submitted']:4d} "
                  f"M={v['M']:9.3f} build={v['build_s_median']*1000:7.2f}ms "
                  f"adapt={v['adapt_s_median']*1000:7.2f}ms total={v['total_s_median']*1000:7.2f}ms")


if __name__ == "__main__":
    main()
