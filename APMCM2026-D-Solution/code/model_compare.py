# -*- coding: utf-8 -*-
"""模型对照实验（回应 GPT 方案里的 RF/XGBoost/LightGBM 比较要求）
指标：RMSE / MAE / R² / Spearman / 低 V 区间 MAE / Top-K 命中
"""
import warnings, json
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from mendeleev import element as mel
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from scipy.stats import spearmanr
from paths import DATA, RES, ensure_output_dirs, require_data

ensure_output_dirs()
require_data("02_castelli_train.csv", "03_castelli_val.csv")

tr = pd.read_csv(DATA / "02_castelli_train.csv")
va = pd.read_csv(DATA / "03_castelli_val.csv")
ELEMS = sorted(set(tr.A) | set(tr.B))
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


Xtr, Xva = feat(tr), feat(va)
ytr, yva = tr.V.values, va.V.values
q10 = np.percentile(yva, 10)
print(f"训练 {len(tr)} / 验证 {len(va)} | 验证集 V 的 10% 分位 = {q10:.2f}")

models = {
    "RandomForest": RandomForestRegressor(n_estimators=400, min_samples_leaf=2, n_jobs=-1, random_state=0),
    "HistGB(GBDT)": HistGradientBoostingRegressor(max_iter=600, learning_rate=0.05, max_leaf_nodes=31,
                                                  min_samples_leaf=20, l2_regularization=1.0, random_state=0),
}
try:
    from xgboost import XGBRegressor
    models["XGBoost"] = XGBRegressor(n_estimators=800, learning_rate=0.05, max_depth=6,
                                     subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0,
                                     n_jobs=-1, random_state=0, tree_method="hist")
except Exception as e:
    print("XGBoost 不可用:", e)
try:
    from lightgbm import LGBMRegressor
    models["LightGBM"] = LGBMRegressor(n_estimators=800, learning_rate=0.05, num_leaves=31,
                                       subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0,
                                       random_state=0, verbose=-1)
except Exception as e:
    print("LightGBM 不可用:", e)

rows = []
preds = {}
for name, m in models.items():
    m.fit(Xtr, ytr)
    p = m.predict(Xva)
    preds[name] = p
    row = dict(model=name,
               RMSE=round(float(np.sqrt(mean_squared_error(yva, p))), 3),
               MAE=round(float(mean_absolute_error(yva, p)), 3),
               R2=round(float(r2_score(yva, p)), 4),
               Spearman=round(float(spearmanr(yva, p).correlation), 4),
               MAE_low10=round(float(mean_absolute_error(yva[yva <= q10], p[yva <= q10])), 3),
               Top20=len(set(np.argsort(yva)[:20]) & set(np.argsort(p)[:20])),
               Top50=len(set(np.argsort(yva)[:50]) & set(np.argsort(p)[:50])),
               Top100=len(set(np.argsort(yva)[:100]) & set(np.argsort(p)[:100])),
               Recall_Vlt2=round(float((p[yva < 2] < 5).mean()) if (yva < 2).any() else np.nan, 3))
    rows.append(row)
    print(f"{name:14s} RMSE={row['RMSE']:7.3f} MAE={row['MAE']:6.3f} R²={row['R2']:.4f} "
          f"ρ={row['Spearman']:.4f} MAE_low10={row['MAE_low10']:6.2f} Top100={row['Top100']}")

df = pd.DataFrame(rows).sort_values("MAE")
df.to_csv(RES / "model_compare.csv", index=False, encoding="utf-8-sig")
print("\n" + df.to_string(index=False))
print(f"\n已存 {RES / 'model_compare.csv'}")
