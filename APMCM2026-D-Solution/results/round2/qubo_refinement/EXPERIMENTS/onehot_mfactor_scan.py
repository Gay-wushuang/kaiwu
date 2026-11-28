# -*- coding: utf-8 -*-
"""T002-A V4：one-hot 罚项尺度扫描（B 输入 topk=8，全空间）。
只做本地验证，不提交真机。"""
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
import kaiwu.preprocess as pp            # noqa: E402
import synthetic_encoding_benchmark as SB  # noqa: E402

OUT = Path(__file__).resolve().parent
INPUTS = ["B-Q2-NO2", "B-Q3-O3", "B-Q3-FO2"]
TOPK = 8
RATIOS = [1.02, 1.05, 1.075, 1.10, 1.20, 1.40, 1.60, 1.80, 2.00,
          2.20, 2.50, 2.80, 3.10, 3.50]


def resolutions(V, M):
    d = V.shape[0]
    Q, _ = SB.build_onehot(V, M)
    I, _ = S.to_ising(Q)
    raw = float(S.resolution(I, d, d)["resol"])
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    Ia = np.abs(adj)
    step = Ia.max() / 127.0
    obj = Ia[:d, d:2 * d].max()
    return raw, float(obj / step)


t0 = time.perf_counter()
out = {}
for version in INPUTS:
    e = exin.load(version)
    A, B, V = dx.select_topk(e.A, e.B, e.V, TOPK)
    vmax = float(V.max())
    _, _, M0 = S.build_qubo(V)
    rows = []
    for ratio in RATIOS:
        M = ratio * vmax
        r = SB.eval_instance(V, M, "onehot")
        raw_res, adj_res = resolutions(V, M)
        r.update({"M": float(M), "M_over_maxV": ratio, "mfactor": float(M / M0),
                  "resol_raw": raw_res, "resol_adj": adj_res})
        rows.append(r)
    # 两类指标分开：合法域集合相等 vs 量化全空间最优仍合法
    legal_set_equal = [r["M_over_maxV"] for r in rows if r["legal_set_equal"]]
    quant_fullspace_ok = [r["M_over_maxV"] for r in rows if r["quant_valid"]]
    global_keep = [r["M_over_maxV"] for r in rows
                   if r["legal_set_equal"] and r["quant_valid"]]
    out[version] = {
        "A": A, "B": B, "V": V.tolist(), "vmax": vmax, "M0": float(M0),
        "rows": rows,
        "legal_set_equal_ratios": legal_set_equal,
        "quant_fullspace_valid_ratios": quant_fullspace_ok,
        "set_equal_ratios": global_keep,
        "best_retention": max(r["retention"] for r in rows),
        "best_spearman": max(r["spearman"] for r in rows if r["spearman"] is not None),
    }
payload = {"schema_version": 1, "scope": "local full-space one-hot M scan; not real machine",
           "inputs": INPUTS, "topk": TOPK, "ratios": RATIOS,
           "results": out, "runtime_s": time.perf_counter() - t0}
(OUT / "onehot_mfactor_scan_results.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({v: {"legal_set_equal_ratios": out[v]["legal_set_equal_ratios"],
                      "quant_fullspace_valid_ratios": out[v]["quant_fullspace_valid_ratios"],
                      "set_equal_ratios": out[v]["set_equal_ratios"],
                      "best_retention": out[v]["best_retention"],
                      "best_spearman": out[v]["best_spearman"]}
                  for v in INPUTS}, ensure_ascii=False, indent=2))
