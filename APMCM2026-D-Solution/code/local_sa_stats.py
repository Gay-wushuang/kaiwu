# -*- coding: utf-8 -*-
"""本地模拟退火：在同样的 8bit 整数 Ising 矩阵上跑大量重启，得到合法率与命中的统计量（免费、可重复）"""
import json
import numpy as np, pandas as pd
import d_submit_cim as S
import kaiwu.preprocess as pp
from paths import CIM_SAMPLES, ensure_output_dirs

ensure_output_dirs()
RES = S.RES


def build(topk, mfactor):
    A, B, V = S.load_pool(topk=topk)
    Q, off, M0 = S.build_qubo(V)
    M = M0 * mfactor
    if mfactor != 1:
        Q, off, M = S.build_qubo(V, M=M)
    I, _ = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    return A, B, V, adj, M


def anneal(adj, n_restart=3000, sweeps=400, T0=3000.0, T1=1.0, seed=0):
    rng = np.random.default_rng(seed)
    n = adj.shape[0]
    out = np.empty((n_restart, n), dtype=np.int8)
    for r in range(n_restart):
        s = rng.choice([-1, 1], size=n).astype(np.float64)
        T = T0
        alpha = (T1 / T0) ** (1.0 / sweeps)
        for t in range(sweeps):
            i = rng.integers(n)
            # ΔH for flipping spin i: H = -sᵀJs  →  ΔH = 2 s_i (J s)_i
            h = adj[i] @ s
            dH = 2.0 * s[i] * h - 2.0 * adj[i, i]   # 对角项修正（J_ii 只在 s_i 一次方出现）
            if dH <= 0 or rng.random() < np.exp(-dH / max(T, 1e-9)):
                s[i] = -s[i]
            T *= alpha
        out[r] = s.astype(np.int8)
    return out


def stats(A, B, V, adj, tag, n_restart=3000):
    sols = anneal(adj, n_restart=n_restart)
    nA, nB = len(A), len(B)
    H = np.array([-s.astype(float) @ adj @ s.astype(float) for s in sols])
    rows = []
    for k, s in enumerate(sols):
        bits = ((s.astype(int) + 1) // 2)[:nA + nB]
        ai = [i for i in range(nA) if bits[i] == 1]
        bi = [i - nA for i in range(nA, nA + nB) if bits[i] == 1]
        ok = len(ai) == 1 and len(bi) == 1
        rows.append(dict(k=k, H=H[k], valid=ok,
                         V=V[ai[0], bi[0]] if ok else np.nan,
                         rank=int((V < V[ai[0], bi[0]]).sum()) + 1 if ok else -1))
    df = pd.DataFrame(rows)
    v = df[df.valid]
    res = dict(tag=tag, n=len(df), valid_rate=round(float(df.valid.mean()), 4),
               H_best=float(df.H.max()), H_median=float(df.H.median()),
               best_V=float(v.V.min()) if len(v) else None,
               hit_top8=float((v["rank"] <= 8).mean()) if len(v) else 0.0)
    if len(v):
        res["best_rank"] = int(v.loc[v.V.idxmin(), "rank"])
    print(f"\n[{tag}] {len(df)} 次重启 | 合法率 {res['valid_rate']*100:.1f}% | "
          f"H 最优 {res['H_best']:.0f} / 中位 {res['H_median']:.0f} | "
          f"合法解最优 V*={res['best_V']}（子问题内第 {res.get('best_rank')}）")
    return res, df


allres = []
for topk, mf in [(13, 1.0), (13, 3.0), (8, 1.0)]:
    A, B, V, adj, M = build(topk, mf)
    tag = f"topk{topk}_Mx{mf:g}"
    r, df = stats(A, B, V, adj, tag)
    r.update(topk=topk, mfactor=mf, M=M)
    allres.append(r)
    df.to_csv(CIM_SAMPLES / f"local_sa_{tag}_samples.csv", index=False, encoding="utf-8-sig")

pd.DataFrame(allres).to_csv(RES / "local_sa_stats.csv", index=False, encoding="utf-8-sig")
print(f"\n已存 {RES / 'local_sa_stats.csv'}")
