# -*- coding: utf-8 -*-
"""比较 B-Q2-NO2 topk=8 在 M0 与 lowM 下的 QUBO/Ising 系数与量化误差。"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))
import experiment_input as exin          # noqa: E402
import d_experiment as dx                # noqa: E402
import d_submit_cim as S                 # noqa: E402

OUT = Path(__file__).resolve().parent
e = exin.load("B-Q2-NO2")
A, B, V = dx.select_topk(e.A, e.B, e.V, 8)
_, _, M0 = S.build_qubo(V)
mf = (1.05 * V.max()) / M0
p0 = dx.build_problem(e, topk=8, mfactor=1.0)
p1 = dx.build_problem(e, topk=8, mfactor=float(mf))
rows = {}
for name, x, y in (("Q", p0["Q"], p1["Q"]), ("I", p0["I"], p1["I"]),
                   ("adj", p0["adj"], p1["adj"])):
    mask = np.abs(x - y) > 1e-12
    rows[name] = {"shape": list(x.shape),
                  "diff_count": int(mask.sum()),
                  "diff_count_definition": "满足 |a-b|>1e-12 的矩阵位置数",
                  "independent_edges": int(np.triu(mask).sum()),
                  "max_abs_diff": float(np.max(np.abs(x - y)))}
for tag, raw, adj in (("M0", p0["I"], p0["adj"]), ("lowM", p1["I"], p1["adj"])):
    step = float(np.abs(raw).max() / 127.0)
    err = np.abs(adj - raw / step)
    rows[tag] = {"step": step,
                 "round_mean": float(err.mean()),
                 "round_mean_unit": "量化步长（含零项与对称位置的全矩阵平均）",
                 "round_mean_in_original_units": float(err.mean() * step),
                 "round_max": float(err.max()),
                 "round_max_unit": "量化步长（全矩阵最大值）",
                 "nonzero_adj": int(np.count_nonzero(adj)),
                 "max_abs_I": float(np.abs(raw).max()),
                 "max_abs_adj": float(np.abs(adj).max()),
                 "resol_raw": float(p0["resol_raw"] if tag == "M0" else p1["resol_raw"]),
                 "resol_adj": float(p0["resol_adj"] if tag == "M0" else p1["resol_adj"])}
payload = {"input": "B-Q2-NO2", "topk": 8, "A": A, "B": B,
           "M0": float(M0), "M_low": float(p1["M"]), "mfactor": float(mf),
           "target_block_equal": bool(np.array_equal(p0["Q"][:8, 8:16], p1["Q"][:8, 8:16])),
           "target_block_check": "np.array_equal（逐元素严格相等，无相对容差）",
           "coeff": rows}
(OUT / "lowm_coeff_delta.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
