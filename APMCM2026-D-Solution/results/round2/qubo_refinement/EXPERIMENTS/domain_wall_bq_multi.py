# -*- coding: utf-8 -*-
"""T002-A V2：在冻结 B 输入的 topk=8 上做 one-hot/domain-wall 全空间本地对照。
不提交真机，不修改第一轮数据。"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_input as exin          # noqa: E402
import d_experiment as dx                # noqa: E402
import d_submit_cim as S                 # noqa: E402
import synthetic_encoding_benchmark as SB  # noqa: E402

OUT = Path(__file__).resolve().parent
INPUTS = ["B-Q2-NO2", "B-Q3-O3", "B-Q3-FO2"]
TOPK = 8
RATIOS = [1.05, 4.0, 8.0, 16.0]
t0 = time.perf_counter()
result = {}
for version in INPUTS:
    e = exin.load(version)
    A, B, V = dx.select_topk(e.A, e.B, e.V, TOPK)
    vmax = float(V.max())
    _, _, M0 = S.build_qubo(V)
    rows = []
    for enc in ("onehot", "domainwall"):
        variants = ([("M0", M0), ("lowM", 1.05 * vmax)] if enc == "onehot"
                    else [(f"ratio{r:g}", r * vmax) for r in RATIOS])
        for variant, M in variants:
            r = SB.eval_instance(V, M, enc)
            r.update({"encoding": enc, "variant": variant, "M": float(M),
                      "M_over_maxV": float(M / vmax)})
            rows.append(r)
    result[version] = {
        "A": A, "B": B, "V": V.tolist(), "vmin": float(V.min()), "vmax": vmax,
        "M0": float(M0),
        "rows": rows,
        "summary": {
            enc: {
                "variants": [r["variant"] for r in rows if r["encoding"] == enc],
                "ratios": [r["M_over_maxV"] for r in rows if r["encoding"] == enc],
                "exact_valid": [r["exact_valid"] for r in rows if r["encoding"] == enc],
                "quant_valid": [r["quant_valid"] for r in rows if r["encoding"] == enc],
                "retention": [r["retention"] for r in rows if r["encoding"] == enc],
                "non_original": [r["non_original"] for r in rows if r["encoding"] == enc],
                "spearman": [r["spearman"] for r in rows if r["encoding"] == enc],
                "exact_gap": [r["exact_gap"] for r in rows if r["encoding"] == enc],
                "quant_gap": [r["quant_gap"] for r in rows if r["encoding"] == enc],
                "n_var": next(r["n_var"] for r in rows if r["encoding"] == enc),
                "n_ising": next(r["n_ising"] for r in rows if r["encoding"] == enc),
                "aux": next(r["aux"] for r in rows if r["encoding"] == enc),
            } for enc in ("onehot", "domainwall")
        },
    }
payload = {
    "schema_version": 1,
    "scope": "local full-space control on frozen B inputs topk=8; not a real-machine run",
    "inputs": INPUTS, "topk": TOPK,
    "results": result,
    "runtime_s": time.perf_counter() - t0,
}
(OUT / "domain_wall_bq_multi_results.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({v: {enc: result[v]["summary"][enc] for enc in ("onehot", "domainwall")}
                  for v in INPUTS}, ensure_ascii=False, indent=2))
