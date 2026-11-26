# -*- coding: utf-8 -*-
"""D 题 问题 1 基线：组分 → V 的代理模型（零正例、按 (A,B) 分组的真实切分验证）"""
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

elems = sorted(set(tr.A) | set(tr.B))
xcat = sorted(tr.X.unique())
ei = {e: i for i, e in enumerate(elems)}
xi = {x: i for i, x in enumerate(xcat)}


def feat(df):
    n = len(df)
    X = np.zeros((n, len(elems) * 2 + len(xcat) + 1), dtype=np.float32)
    ai = df.A.map(ei).values
    bi = df.B.map(ei).values
    xv = df.X.map(xi).values
    rows = np.arange(n)
    X[rows, ai] = 1
    X[rows, len(elems) + bi] = 1
    X[rows, 2 * len(elems) + xv] = 1
    X[:, -1] = df.a_eq_b.values
    return X


Xtr, ytr = feat(tr), tr.V.values
Xva, yva = feat(va), va.V.values
print(f"特征维: {Xtr.shape[1]} | 训练 {len(tr)} | 验证 {len(va)}")

res = {}
for tag, tf, inv in [("直接预测 V", lambda y: y, lambda z: z),
                     ("log1p(V)", np.log1p, lambda z: np.expm1(z))]:
    m = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, max_leaf_nodes=31,
                                      min_samples_leaf=20, l2_regularization=1.0, random_state=0)
    m.fit(Xtr, tf(ytr))
    p = inv(m.predict(Xva))
    res[tag] = (r2_score(yva, p), mean_absolute_error(yva, p), p, m)
    print(f"{tag}: 验证 R²={r2_score(yva,p):.4f} | MAE={mean_absolute_error(yva,p):.3f}")

best = min(res.items(), key=lambda kv: kv[1][1])   # 按 MAE 选
tag, (r2, mae, pva, model) = best
print(f"\n采用: {tag}")

# 排序能力：真值最小的 50 个里，模型预测最小的 50 个命中几个
k = 50
true_top = set(np.argsort(yva)[:k])
pred_top = set(np.argsort(pva)[:k])
print(f"Top-{k} 命中率: {len(true_top & pred_top)}/{k}")
for th in [0.5, 1, 2]:
    idx = yva < th
    print(f"  V<{th}: 真值 {idx.sum()} 个，其预测均值 {pva[idx].mean():.3f}（全体均值 {pva.mean():.3f}）")

# 池子预测（问题 2：X=NO2 的 52x52）
Xp = feat(pool)
if tag == "log1p(V)":
    pv = np.expm1(model.predict(Xp))
else:
    pv = model.predict(Xp)
pool = pool.assign(V_hat=pv).sort_values("V_hat")
print("\n07 池（X=NO2，2704 个 (A,B)）预测最优前 10：")
print(pool[["formula", "A", "B", "V_hat"]].head(10).to_string(index=False))
print("\n预测 V 最小的 10 个分布：min %.3f 中位 %.3f max %.3f" % (pv.min(), np.median(pv), pv.max()))
pool.to_csv(RES / "q2_pool_pred.csv", index=False, encoding="utf-8-sig")
print(f"已存 {RES / 'q2_pool_pred.csv'}")
