# -*- coding: utf-8 -*-
"""T002-A V4：one-hot 量化后合法能量误差结构（本地，不提交真机）。

对每个 (输入, M/Vmax) 计算：
  1. 合法 8x8 标签上的量化能量 E_q(i,j)（辅助位按其自身最优取值，与真机解码一致：
     解码只看前 2d 位，辅助位不参与合法性判定）；
  2. 以 E_q ~ alpha*V + beta 最小二乘拟合，得到残差 R(i,j)（整数单位）；
  3. 把 R 做两向可加分解 R(i,j) = c + a_i + b_j + W(i,j)，报告行/列/交互 RMS；
  4. 检查量化最优集合与原始最优集合的差异，以及决定翻转所需的
     “原始 V 间隙”与“残差差”对比。
"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_input as exin          # noqa: E402
import d_experiment as dx                # noqa: E402
import d_submit_cim as S                 # noqa: E402
import kaiwu as kw                       # noqa: E402
import kaiwu.preprocess as pp            # noqa: E402
import synthetic_encoding_benchmark as SB  # noqa: E402

OUT = Path(__file__).resolve().parent
CASES = {
    "B-Q2-NO2": [1.02, 1.05, 1.075, 1.10, 1.20, 1.40, 2.80, 3.1041],
    "B-Q3-FO2": [1.02, 1.05, 2.20],
}
TOPK = 8


def quant_legal_matrix(V, M):
    d = V.shape[0]
    Q, _ = SB.build_onehot(V, M)
    I, _ = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    Qa, offa = kw.core.ising_matrix_to_qubo_matrix(adj)
    n = Qa.shape[0]
    E = np.zeros((d, d))
    for r in range(d):
        for q in range(d):
            best = None
            for aux in (0.0, 1.0):
                x = np.zeros(n)
                x[r] = 1.0
                x[d + q] = 1.0
                x[-1] = aux
                e = float(x @ Qa @ x) + offa
                best = e if best is None else min(best, e)
            E[r, q] = best
    return E


def two_way(R):
    """R(i,j) = c + a_i + b_j + W(i,j)，最小二乘可加分解。"""
    c = float(R.mean())
    a = R.mean(axis=1) - c
    b = R.mean(axis=0) - c
    W = R - (c + a[:, None] + b[None, :])
    return {
        "grand_mean": c,
        "row_rms": float(np.sqrt(np.mean(a ** 2))),
        "col_rms": float(np.sqrt(np.mean(b ** 2))),
        "row_range": float(a.max() - a.min()),
        "col_range": float(b.max() - b.min()),
        "interaction_rms": float(np.sqrt(np.mean(W ** 2))),
        "interaction_max_abs": float(np.abs(W).max()),
    }


t0 = time.perf_counter()
payload = {"schema_version": 1,
           "scope": "local error-structure analysis on quantized legal energies; not real machine",
           "topk": TOPK, "cases": {}}
for version, ratios in CASES.items():
    e = exin.load(version)
    A, B, V = dx.select_topk(e.A, e.B, e.V, TOPK)
    vmax = float(V.max())
    _, _, M0 = S.build_qubo(V)
    distinct = np.unique(np.sort(V.flatten()))
    raw_gap = float(distinct[1] - distinct[0]) if len(distinct) > 1 else None
    raw_min = float(V.min())
    raw_set = {(int(i), int(j)) for i, j in zip(*np.where(np.abs(V - raw_min) < 1e-12))}
    cases = []
    for ratio in ratios:
        M = ratio * vmax
        E = quant_legal_matrix(V, M)
        flat = E.flatten()
        Vf = V.flatten()
        alpha, beta = np.polyfit(Vf, flat, 1)
        R = E - (alpha * V + beta)
        qmin = flat.min()
        qset = {(int(i), int(j)) for i, j in np.argwhere(np.abs(E - qmin) < 1e-9)}
        R_raw_opts = [float(R[i, j]) for (i, j) in sorted(raw_set)]
        Rmin = min(R_raw_opts)
        second = distinct[1] if len(distinct) > 1 else None
        runner_up = []
        if second is not None:
            for i, j in np.argwhere(np.abs(V - second) < 1e-12):
                runner_up.append({
                    "label": [int(i), int(j)], "V": float(V[i, j]),
                    "dV_vs_raw_opt": float(V[i, j] - raw_min),
                    "quant_margin_units": float(E[i, j] - qmin),
                    "residual": float(R[i, j]),
                })
        flips = []
        for (i, j) in sorted(qset - raw_set):
            flips.append({
                "label": [i, j],
                "V": float(V[i, j]),
                "dV_vs_raw_opt": float(V[i, j] - raw_min),
                "residual_minus_raw_opt": float(R[i, j] - Rmin),
                "residual_minus_raw_opt_in_V_units": float((R[i, j] - Rmin) / alpha),
            })
        cases.append({
            "M_over_maxV": ratio, "M": float(M), "mfactor": float(M / M0),
            "fit_alpha": float(alpha), "fit_beta": float(beta),
            "residual_rms": float(np.sqrt(np.mean(R ** 2))),
            "residual_max_abs": float(np.abs(R).max()),
            "residual_range": float(R.max() - R.min()),
            "two_way": two_way(R),
            "raw_distinct_gap": raw_gap,
            "raw_set": sorted([list(x) for x in raw_set]),
            "raw_opt_residuals": R_raw_opts,
            "runner_up": runner_up,
            "quant_set": sorted([list(x) for x in qset]),
            "set_equal": raw_set == qset,
            "residual_matrix": R.tolist(),
            "flip_details": flips,
        })
    payload["cases"][version] = {"vmax": vmax, "M0": float(M0),
                                 "raw_distinct_gap": raw_gap, "rows": cases}
payload["runtime_s"] = time.perf_counter() - t0

(OUT / "onehot_quant_error_structure.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

for version, d in payload["cases"].items():
    print(f"=== {version} raw_gap={d['raw_distinct_gap']:.4f}")
    for r in d["rows"]:
        tw = r["two_way"]
        print(f"  M/Vmax={r['M_over_maxV']:.4f} alpha={r['fit_alpha']:.3f} "
              f"Rrms={r['residual_rms']:.2f} Rrange={r['residual_range']:.2f} "
              f"row_range={tw['row_range']:.2f} col_range={tw['col_range']:.2f} "
              f"Wrms={tw['interaction_rms']:.2f} set_equal={r['set_equal']} "
              f"flips={len(r['flip_details'])}")
