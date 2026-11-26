# -*- coding: utf-8 -*-
"""最终代理模型（物理量路线）：02+03 训练 e_form/gap(两阶段)/vbm/cbm，再按公式组 V*"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from mendeleev import element as mel
from xgboost import XGBRegressor, XGBClassifier
from paths import DATA, PRED, ensure_output_dirs, require_data

ensure_output_dirs()
require_data("02_castelli_train.csv", "03_castelli_val.csv", "07_castelli_q2_pool.csv",
             "08_castelli_q3_pool.csv", "11_castelli_q2_pool_blind.csv",
             "12_castelli_q3_pool_blind.csv")

tr = pd.read_csv(DATA / "02_castelli_train.csv")
va = pd.read_csv(DATA / "03_castelli_val.csv")
al = pd.concat([tr, va], ignore_index=True)
pools = {k: pd.read_csv(DATA / f) for k, f in [
    ("q2", "07_castelli_q2_pool.csv"), ("q3", "08_castelli_q3_pool.csv"),
    ("q2b", "11_castelli_q2_pool_blind.csv"), ("q3b", "12_castelli_q3_pool_blind.csv")]}

ELEMS = sorted(set(al.A) | set(al.B))
P = {}
for s in ELEMS:
    e = mel(s)
    P[s] = dict(Z=e.atomic_number, group=e.group_id or 0, period=e.period,
                en=e.electronegativity_pauling() or np.nan, rad=e.atomic_radius or np.nan,
                vol=e.atomic_volume or np.nan, mass=e.mass)
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
    cols.append(xn.sum(1)); cols += [xn[:, j] for j in range(4)]
    cols.append(np.abs(pa["en"].values - 3.44))
    return np.column_stack(cols).astype(np.float32)


def Vof(ef, gp, vb, cb):
    p = lambda v: np.square(np.maximum(0, np.divide(v, 0.5, dtype=np.float64)))
    return p(ef - 0.21) + p(1.4 - gp) + p(gp - 3.1) + p(5.73 - vb) + p(cb - 4.50)


MK = dict(n_estimators=800, learning_rate=0.05, max_depth=6, subsample=0.9,
          colsample_bytree=0.9, reg_lambda=1.0, n_jobs=-1, random_state=0, tree_method="hist")
Xa = feat(al)
reg = {}
for col in ["e_form", "vbm", "cbm"]:
    reg[col] = XGBRegressor(**MK).fit(Xa, al[col].values)
clf = XGBClassifier(n_estimators=600, learning_rate=0.05, max_depth=5, subsample=0.9,
                    colsample_bytree=0.9, reg_lambda=1.0, n_jobs=-1, random_state=0,
                    tree_method="hist", eval_metric="logloss")
clf.fit(Xa, (al.gap > 0).astype(int))
sub = (al.gap > 0).values
greg = XGBRegressor(**MK).fit(Xa[sub], al.gap.values[sub])
print(f"物理量路线：02+03 共 {len(al)} 行训练（gap 两阶段：分类 + 回归）")

out = {}
for k, df in pools.items():
    Xp = feat(df)
    gp = clf.predict_proba(Xp)[:, 1] * greg.predict(Xp)
    v = Vof(reg["e_form"].predict(Xp), gp, reg["vbm"].predict(Xp), reg["cbm"].predict(Xp))
    d2 = df.assign(V_hat=v).sort_values("V_hat")
    d2.to_csv(PRED / f"pool_{k}_phys.csv", index=False, encoding="utf-8-sig")
    out[k] = d2
    print(f"\n池 {k}: {len(df)} 个 | V_hat min {v.min():.3f} 中位 {np.median(v):.2f} | V_hat<1 的 {int((v<1).sum())} 个")
    print(d2[["formula", "A", "B", "X", "V_hat"]].head(5).to_string(index=False))

V2 = out["q2"].pivot_table(index="A", columns="B", values="V_hat", aggfunc="first")
A = list(V2.index); B = list(V2.columns); Vmat = V2.values
import kaiwu as kw

def qubo(V, M):
    nA, nB = V.shape; n = nA + nB
    Q = np.zeros((n, n)); Q[:nA, nA:] = V
    for base, k in [(0, nA), (nA, nB)]:
        for i in range(base, base + k):
            Q[i, i] -= M
            for j in range(i + 1, base + k):
                Q[i, j] += 2 * M
    return Q

print("\n=== 物理量路线下的 QUBO 精度分析（问题 2）")
for tag, K2 in [("全量 52×52", 0), ("预筛 13×13", 13)]:
    Vv = Vmat if not K2 else Vmat[np.ix_(np.argsort(Vmat.min(1))[:K2], np.argsort(Vmat.min(0))[:K2])]
    M = max(2 * (Vv.max() - Vv.min()), 1) + 15
    Q = qubo(Vv, M)
    I, _ = kw.core.qubo_matrix_to_ising_matrix(Q)
    Ia = np.abs(np.asarray(I, float))
    nA, nB = Vv.shape
    i, j = np.unravel_index(Vv.argmin(), Vv.shape)
    nm = (([A[k] for k in np.argsort(Vmat.min(1))[:K2]] if K2 else A)[i],
          ([B[k] for k in np.argsort(Vmat.min(0))[:K2]] if K2 else B)[j])
    step = Ia.max() / 127; obj = Ia[:nA, nA:nA + nB].max()
    print(f"{tag}: {Q.shape[0]} 比特(M={M:.0f}) | max|J|={Ia.max():.0f} | 目标块 {obj:.2f} | "
          f"步长 {step:.2f} | 可分档数 {obj/step:.2f} | 最优 {nm[0]}-{nm[1]} V*={Vv[i,j]:.4f}")
