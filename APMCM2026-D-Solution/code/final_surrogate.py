# -*- coding: utf-8 -*-
"""最终代理模型：按题面口径用 02+03 训练（模型按验证集选出的 XGBoost），重算四个池子并重建 QUBO"""
import os, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from mendeleev import element as mel
from xgboost import XGBRegressor

ROOT = r"D:\比赛\APMCM\D题"
DAT = os.path.join(ROOT, "date")
CODE = os.path.join(ROOT, "code")
RES = os.path.join(ROOT, "results")

tr = pd.read_csv(os.path.join(DAT, "02_castelli_train.csv"))
va = pd.read_csv(os.path.join(DAT, "03_castelli_val.csv"))
allab = pd.concat([tr, va], ignore_index=True)
pools = {k: pd.read_csv(os.path.join(DAT, f)) for k, f in [
    ("q2", "07_castelli_q2_pool.csv"), ("q3", "08_castelli_q3_pool.csv"),
    ("q2b", "11_castelli_q2_pool_blind.csv"), ("q3b", "12_castelli_q3_pool_blind.csv")]}

ELEMS = sorted(set(allab.A) | set(allab.B))
P = {}
for s in ELEMS:
    e = mel(s)
    P[s] = dict(Z=e.atomic_number, group=e.group_id or 0, period=e.period,
                en=e.electronegativity_pauling() or np.nan,
                rad=e.atomic_radius or np.nan, vol=e.atomic_volume or np.nan, mass=e.mass)
P = pd.DataFrame(P).T
for c in ["en", "rad", "vol"]:
    P[c] = P[c].fillna(P[c].median())
K = ["Z", "group", "period", "en", "rad", "vol", "mass"]
XCOMP = {"O3": (0, 0, 3, 0), "NO2": (1, 0, 2, 0), "FO2": (0, 1, 2, 0),
         "N2O": (2, 0, 1, 0), "N3": (3, 0, 0, 0), "O2S": (0, 0, 2, 1), "FNO": (0, 1, 1, 1)}


def feat(df):
    pa, pb = P.loc[df.A.values], P.loc[df.B.values]
    cols = []
    for k in K:
        a, b = pa[k].values.astype(float), pb[k].values.astype(float)
        cols += [a, b, np.abs(a - b), a + b]
    cols.append(df.a_eq_b.values.astype(float))
    xn = np.array([XCOMP[x] for x in df.X.values], dtype=float)
    cols.append(xn.sum(1))
    cols += [xn[:, j] for j in range(4)]
    cols.append(np.abs(pa["en"].values - 3.44))
    return np.column_stack(cols).astype(np.float32)


X = feat(allab); y = allab.V.values
model = XGBRegressor(n_estimators=800, learning_rate=0.05, max_depth=6, subsample=0.9,
                     colsample_bytree=0.9, reg_lambda=1.0, n_jobs=-1, random_state=0,
                     tree_method="hist")
model.fit(X, y)
print(f"最终 V̂：XGBoost 在 02+03 共 {len(allab)} 行上训练")

files = {"q2": "pool_q2_final.csv", "q3": "pool_q3_final.csv",
         "q2b": "pool_q2b_final.csv", "q3b": "pool_q3b_final.csv"}
out = {}
for k, df in pools.items():
    v = model.predict(feat(df))
    d2 = df.assign(V_hat=v).sort_values("V_hat")
    d2.to_csv(os.path.join(CODE, files[k]), index=False, encoding="utf-8-sig")
    out[k] = d2
    print(f"\n池 {k}: {len(df)} 个 | V_hat min {v.min():.3f} / 中位 {np.median(v):.2f} | V_hat<1 的 {int((v<1).sum())} 个")
    print(d2[["formula", "A", "B", "X", "V_hat"]].head(5).to_string(index=False))

# 重建 QUBO（问题 2，全量与 top-13）
import kaiwu as kw
import kaiwu.preprocess as pp

V2 = out["q2"].pivot_table(index="A", columns="B", values="V_hat", aggfunc="first")
A = list(V2.index); B = list(V2.columns)
Vmat = V2.values


def qubo(V, M):
    nA, nB = V.shape; n = nA + nB
    Q = np.zeros((n, n)); Q[:nA, nA:] = V
    for base, k in [(0, nA), (nA, nB)]:
        for i in range(base, base + k):
            Q[i, i] -= M
            for j in range(i + 1, base + k):
                Q[i, j] += 2 * M
    return Q


print("\n=== 新 V̂ 下的 QUBO 精度分析（问题 2）")
for tag, K2 in [("全量 52×52", 0), ("预筛 13×13", 13)]:
    if K2:
        ia = np.argsort(Vmat.min(1))[:K2]; ib = np.argsort(Vmat.min(0))[:K2]
        Vv = Vmat[np.ix_(ia, ib)]
    else:
        Vv = Vmat
    M = max(2 * (Vv.max() - Vv.min()), 1) + 15
    Q = qubo(Vv, M)
    I, bias = kw.core.qubo_matrix_to_ising_matrix(Q)
    Ia = np.abs(np.asarray(I, float))
    nA, nB = Vv.shape
    step = Ia.max() / 127
    obj = Ia[:nA, nA:nA + nB].max()
    i, j = np.unravel_index(Vv.argmin(), Vv.shape)
    nm = ([A[k] for k in ia] if K2 else A)[i], ([B[k] for k in ib] if K2 else B)[j]
    print(f"{tag}: {Q.shape[0]} 比特(M={M:.0f}) | max|J|={Ia.max():.0f} | 目标块 {obj:.1f} | "
          f"步长 {step:.2f} | 可分档数 {obj/step:.2f} | 穷举最优 {nm[0]}-{nm[1]} V*={Vv[i,j]:.4f}")
