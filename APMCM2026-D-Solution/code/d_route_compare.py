# -*- coding: utf-8 -*-
"""路线对比：直接回归 V  vs  先预测 4 个物理量再按公式算 V"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from paths import DATA, RES, ensure_output_dirs, require_data

ensure_output_dirs()
require_data("02_castelli_train.csv", "03_castelli_val.csv", "07_castelli_q2_pool.csv")
tr = pd.read_csv(DATA / "02_castelli_train.csv")
va = pd.read_csv(DATA / "03_castelli_val.csv")
pool = pd.read_csv(DATA / "07_castelli_q2_pool.csv")
elems = sorted(set(tr.A) | set(tr.B)); xcat = sorted(set(tr.X.unique()))
ei = {e: i for i, e in enumerate(elems)}; xi = {x: i for i, x in enumerate(xcat)}


def feat(df):
    n = len(df)
    X = np.zeros((n, len(elems) * 2 + len(xcat) + 1), dtype=np.float32)
    r = np.arange(n)
    X[r, df.A.map(ei).values] = 1
    X[r, len(elems) + df.B.map(ei).values] = 1
    X[r, 2 * len(elems) + df.X.map(xi).values] = 1
    X[:, -1] = df.a_eq_b.values
    return X


def Vof(ef, gp, vb, cb):
    p = lambda v: np.square(np.maximum(0, v / 0.5))
    with np.errstate(invalid="ignore"):
        return p(ef - 0.21) + p(1.4 - gp) + p(gp - 3.1) + p(5.73 - vb) + p(cb - 4.50)


Xtr, Xva, Xp = feat(tr), feat(va), feat(pool)
MK = dict(max_iter=400, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=20,
          l2_regularization=1.0, random_state=0)

# 路线 A：直接回归 V
mA = HistGradientBoostingRegressor(**MK).fit(Xtr, tr.V.values)
pA = mA.predict(Xva)

# 路线 B：4 个物理量 → 公式组合
pred = {}
for col, cap, lo, hi in [("e_form", 0.21, -1e9, 1e9), ("gap", None, -1e9, 1e9),
                         ("vbm", None, -1e9, 1e9), ("cbm", None, -1e9, 1e9)]:
    m = HistGradientBoostingRegressor(**MK).fit(Xtr, tr[col].values)
    pv = m.predict(Xva)
    print(f"  {col}: 验证 R²={r2_score(va[col].values, pv):.3f} MAE={mean_absolute_error(va[col].values, pv):.3f}")
    pred[col] = (m, pv)
pB = Vof(pred["e_form"][1], pred["gap"][1], pred["vbm"][1], pred["cbm"][1])

yva = va.V.values
print()
print(f"路线A 直接回归 V : R²={r2_score(yva,pA):.4f} MAE={mean_absolute_error(yva,pA):.3f}")
print(f"路线B 物理量→公式: R²={r2_score(yva,pB):.4f} MAE={mean_absolute_error(yva,pB):.3f}")
for name, p in [("A", pA), ("B", pB)]:
    for k in [20, 50, 100]:
        hit = len(set(np.argsort(yva)[:k]) & set(np.argsort(p)[:k]))
        print(f"  路线{name} Top-{k} 命中 {hit}/{k}", end="")
    print()
print()
print("真值 V<1 的样本（27 个）在两条路线下的预测均值: A %.2f | B %.2f（全体均值 %.2f）"
      % (pA[yva < 1].mean(), pB[yva < 1].mean(), pA.mean()))

# 池子（问题 2）
qA = mA.predict(Xp)
qB = Vof(*[pred[c][0].predict(Xp) for c in ["e_form", "gap", "vbm", "cbm"]])
out = pool.assign(V_hat_A=qA, V_hat_B=qB).sort_values("V_hat_B")
print("\n07 池按路线 B 排序前 10：")
print(out[["formula", "A", "B", "V_hat_B", "V_hat_A"]].head(10).to_string(index=False))
print("\n路线B 预测池子最小/中位/最大: %.3f / %.3f / %.3f" % (qB.min(), np.median(qB), qB.max()))
print("路线B 预测 V<1 的池内候选数:", int((qB < 1).sum()), " | V<2:", int((qB < 2).sum()))
out.to_csv(RES / "q2_pool_pred2.csv", index=False, encoding="utf-8-sig")
