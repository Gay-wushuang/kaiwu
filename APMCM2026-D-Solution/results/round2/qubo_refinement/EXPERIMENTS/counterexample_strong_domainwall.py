# -*- coding: utf-8 -*-
"""反例：强罚项 M=1.05*max V 也不保证 domain-wall 全空间约束有效。"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import synthetic_encoding_benchmark as B  # noqa: E402

V = np.ones((4, 4))
for i, j in ((0, 1), (2, 1), (1, 0), (1, 2)):
    V[i, j] = 4.0
M = 1.05 * V.max()
Q, offset = B.build_domain_wall(V, M)
cmap = B.code_map(4, "domainwall")
rows = []
for bits in itertools.product([0, 1], repeat=6):
    x = np.asarray(bits, float)
    e = float(x @ Q @ x) + offset
    ok = tuple(bits[:3]) in cmap and tuple(bits[3:]) in cmap
    rows.append({"bits": list(bits), "energy": e, "legal": ok})
best_legal = min((r for r in rows if r["legal"]), key=lambda r: r["energy"])
best_illegal = min((r for r in rows if not r["legal"]), key=lambda r: r["energy"])
payload = {
    "V": V.tolist(), "M": float(M), "M_over_maxV": float(M / V.max()),
    "best_legal": best_legal, "best_illegal": best_illegal,
    "illegal_minus_legal": best_illegal["energy"] - best_legal["energy"],
    "note": "invalid domain-wall code 010 has negative cross-cost contributions; M based only on Vmax is not sufficient",
}
(HERE / "counterexample_strong_domainwall.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
