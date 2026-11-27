# -*- coding: utf-8 -*-
"""D 题 Step 1+2：元素属性特征 + 多任务物理量预测（gap 两阶段）→ V 预测"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from mendeleev import element as mel
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.metrics import r2_score, mean_absolute_error, roc_auc_score
from paths import DATA, PRED, ensure_output_dirs, require_data

ensure_output_dirs()
require_data("02_castelli_train.csv", "03_castelli_val.csv", "07_castelli_q2_pool.csv",
             "08_castelli_q3_pool.csv", "11_castelli_q2_pool_blind.csv",
             "12_castelli_q3_pool_blind.csv")
tr = pd.read_csv(DATA / "02_castelli_train.csv")
va = pd.read_csv(DATA / "03_castelli_val.csv")
pools = {k: pd.read_csv(DATA / f) for k, f in [
    ("q2", "07_castelli_q2_pool.csv"), ("q3", "08_castelli_q3_pool.csv"),
    ("q2b", "11_castelli_q2_pool_blind.csv"), ("q3b", "12_castelli_q3_pool_blind.csv")]}

ELEMS = sorted(set(tr.A) | set(tr.B))
XC = sorted(tr.X.unique())

# ---- 元素属性表（mendeleev） ----
props = {}
for s in ELEMS:
    e = mel(s)
    props[s] = dict(
        Z=e.atomic_number,
        group=e.group_id or 0,
        period=e.period,
        en=e.electronegativity_pauling() if e.electronegativity_pauling() else np.nan,
        rad=e.atomic_radius if e.atomic_radius else np.nan,
        vol=e.atomic_volume if e.atomic_volume else np.nan,
        mass=e.mass,
    )
P = pd.DataFrame(props).T
P["en"] = P["en"].fillna(P["en"].median())
P["rad"] = P["rad"].fillna(P["rad"].median())
P["vol"] = P["vol"].fillna(P["vol"].median())
print("元素属性表:", P.shape, "| 缺电负性元素:", [s for s in ELEMS if pd.isna(mel(s).electronegativity_pauling())])

# X 位原子组成（化学式里的原子个数）
XCOMP = {"O3": (0, 0, 3, 0), "NO2": (1, 0, 2, 0), "FO2": (0, 1, 2, 0),
         "N2O": (2, 0, 1, 0), "N3": (3, 0, 0, 0), "O2S": (0, 0, 2, 1), "FNO": (0, 1, 1, 1)}
# 顺序: N, F, O, S


def feat(df):
    pa = P.loc[df.A.values]
    pb = P.loc[df.B.values]
    cols = []
    for k in ["Z", "group", "period", "en", "rad", "vol", "mass"]:
        a, b = pa[k].values.astype(float), pb[k].values.astype(float)
        cols += [a, b, np.abs(a - b), a + b]
    cols.append(df.a_eq_b.values.astype(float))
    xn = np.array([XCOMP[x] for x in df.X.values], dtype=float)      # N,F,O,S 个数
    cols.append(xn.sum(axis=1))
    for j in range(4):
        cols.append(xn[:, j])
    # X 与金属的电负性差（用 O 代表阴离子）
    cols.append(np.abs(pa["en"].values - 3.44))   # O 的 Pauling 电负性
    X = np.column_stack(cols).astype(np.float32)
    return X


Xtr, Xva = feat(tr), feat(va)
print("特征维:", Xtr.shape[1])


def Vof(ef, gp, vb, cb):
    p = lambda v: np.square(np.maximum(0, np.divide(v, 0.5, dtype=np.float64)))
    return p(ef - 0.21) + p(1.4 - gp) + p(gp - 3.1) + p(5.73 - vb) + p(cb - 4.50)


MK = dict(max_iter=500, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=20,
          l2_regularization=1.0, random_state=0)

# 直接回归 V（同特征，做对照）
mV = HistGradientBoostingRegressor(**MK).fit(Xtr, tr.V.values)
pV = mV.predict(Xva)
print(f"[对照] 直接回归 V: R²={r2_score(va.V, pV):.4f} MAE={mean_absolute_error(va.V, pV):.3f}")

# 多任务物理量
out = {}
for col in ["e_form", "vbm", "cbm", "a_lat", "volume"]:
    m = HistGradientBoostingRegressor(**MK).fit(Xtr, tr[col].values)
    p = m.predict(Xva)
    out[col] = (m, p)
    print(f"  {col:8s}: R²={r2_score(va[col], p):.3f} MAE={mean_absolute_error(va[col], p):.3f}")

# gap 两阶段：先判是否金属性(gap==0)，再对有带隙样本回归
clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                     min_samples_leaf=20, l2_regularization=1.0, random_state=0)
yt = (tr.gap > 0).astype(int)
clf.fit(Xtr, yt)
pclf = clf.predict_proba(Xva)[:, 1]
print(f"  gap 金属性分类器: AUC={roc_auc_score((va.gap > 0).astype(int), pclf):.3f} | 正类占比 {yt.mean():.3f}")
sub = tr.gap > 0
mgap = HistGradientBoostingRegressor(**MK).fit(Xtr[sub.values], tr.gap.values[sub.values],
                                               sample_weight=None)
pgap_val = mgap.predict(Xva)
pgap = pclf * pgap_val     # 期望带隙
print(f"  gap 两阶段: 验证 R²={r2_score(va.gap, pgap):.3f} MAE={mean_absolute_error(va.gap, pgap):.3f}")

pB = Vof(out["e_form"][1], pgap, out["vbm"][1], out["cbm"][1])
print(f"\n[主路线] 物理量→公式: R²={r2_score(va.V, pB):.4f} MAE={mean_absolute_error(va.V, pB):.3f}")
for k in [20, 50, 100]:
    hit = len(set(np.argsort(va.V.values)[:k]) & set(np.argsort(pV)[:k]))
    hit2 = len(set(np.argsort(va.V.values)[:k]) & set(np.argsort(pB)[:k]))
    print(f"  Top-{k}: 直接回归 {hit}/{k} | 物理量路线 {hit2}/{k}")
print("真值 V<1 的 27 个样本预测均值: 直接 %.2f | 物理量 %.2f" % (pV[va.V < 1].mean(), pB[va.V < 1].mean()))


def predict_pool(df):
    X = feat(df)
    ef = out["e_form"][0].predict(X)
    gp = clf.predict_proba(X)[:, 1] * mgap.predict(X)
    vb = out["vbm"][0].predict(X)
    cb = out["cbm"][0].predict(X)
    return Vof(ef, gp, vb, cb), dict(e_form=ef, gap=gp, vbm=vb, cbm=cb)


for k, df in pools.items():
    v, parts = predict_pool(df)
    df2 = df.assign(V_hat=v, **{f"pred_{c}": parts[c] for c in parts})
    df2.sort_values("V_hat").to_csv(PRED / f"pool_{k}.csv", index=False, encoding="utf-8-sig")
    print(f"\n池 {k}: {len(df)} 个候选 | V_hat min {v.min():.3f} 中位 {np.median(v):.2f} max {v.max():.2f} | V_hat<1 的 {int((v < 1).sum())} 个")
    print(df2.sort_values("V_hat")[["formula", "A", "B", "X", "V_hat"]].head(5).to_string(index=False))
