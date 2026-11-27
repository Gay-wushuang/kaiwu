import ast
import re
import sys
from pathlib import Path

CODE = Path(r"e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\code")
sys.path.insert(0, str(CODE))

import numpy as np
import kaiwu.preprocess as pp
import d_submit_cim as S

BASE = Path(r"C:\Users\ERE.DESKTOP-JD48OPB\AppData\Local\Temp\apmcm_audit_pdf")

TASKS = [
    ("apmcm_q2_no2_k13", 13, 1.0),
    ("apmcm_q2_k13_m3x", 13, 3.0),
    ("apmcm_q2_k8_m1x", 8, 1.0),
]


def parse_pdf(name):
    text = (BASE / f"vendor_{name}" / "pages" / "page_0001.txt").read_text(encoding="utf-8")
    hs = [float(x) for x in re.findall(r"Hamiltonian = (-?[\d.]+)", text)]
    vecs = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            vecs.append(np.array(ast.literal_eval(line), dtype=float))
    return hs, vecs


for name, topk, mf in TASKS:
    A, B, V = S.load_pool(topk=topk)
    Q, off, M0 = S.build_qubo(V)
    M = M0
    if mf != 1.0:
        Q, off, M = S.build_qubo(V, M=M0 * mf)
    I, bias = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    nA, nB = len(A), len(B)
    hs, vecs = parse_pdf(name)

    print(f"=== {name} ===")
    print(f"矩阵: {nA}x{nB} -> Ising {adj.shape[0]} | M={M:.3f} | PDF 解数={len(vecs)}")
    if len(vecs) != len(hs):
        print(f"  !! 向量数 {len(vecs)} 与 Hamiltonian 数 {len(hs)} 不一致")
    h_calc = []
    valid = 0
    for i, s in enumerate(vecs):
        if s.shape[0] != adj.shape[0]:
            print(f"  结果{i+1}: 维度 {s.shape[0]} != 矩阵 {adj.shape[0]}")
            continue
        h = float(-s @ adj @ s)
        h_calc.append(h)
        bits = ((s + 1) // 2).astype(int)[:nA + nB]
        ok = bits[:nA].sum() == 1 and bits[nA:].sum() == 1
        valid += ok
        diff = h - hs[i]
        print(f"  结果{i+1}: PDF H={hs[i]:.1f} | 复算 H={h:.1f} | 差={diff:.1f} | 合法={ok}")
    print(f"  合法解数: {valid} / {len(vecs)}")
    if h_calc:
        print(f"  最大 |ΔH| = {max(abs(h - hh) for h, hh in zip(h_calc, hs)):.3f}")
    print()
