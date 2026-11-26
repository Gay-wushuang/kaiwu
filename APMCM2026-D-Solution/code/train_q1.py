# -*- coding: utf-8 -*-
"""D 题 问题 1 训练脚本（正式版）：多模型对照 + 消融 + 两阶段 gap + 不确定性 + 出图"""
import os, json, warnings, time
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mendeleev import element as mel
from sklearn.ensemble import (HistGradientBoostingRegressor, HistGradientBoostingClassifier,
                             RandomForestRegressor, ExtraTreesRegressor)
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_absolute_error
from scipy.stats import spearmanr

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = r"D:\比赛\APMCM\D题"
DAT = os.path.join(ROOT, "date")
FIG = os.path.join(ROOT, "figures")
RES = os.path.join(ROOT, "results")
os.makedirs(FIG, exist_ok=True)
os.makedirs(RES, exist_ok=True)

tr = pd.read_csv(os.path.join(DAT, "02_castelli_train.csv"))
va = pd.read_csv(os.path.join(DAT, "03_castelli_val.csv"))
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
XC = sorted(tr.X.unique())


def feat(df, onehot=False):
    pa, pb = P.loc[df.A.values], P.loc[df.B.values]
    cols, names = [], []
    for k in K:
        a, b = pa[k].values.astype(float), pb[k].values.astype(float)
        cols += [a, b, np.abs(a - b), a + b]
        names += [f"{k}_A", f"{k}_B", f"d_{k}", f"s_{k}"]
    cols.append(df.a_eq_b.values.astype(float)); names.append("a_eq_b")
    xn = np.array([XCOMP[x] for x in df.X.values], dtype=float)
    cols.append(xn.sum(axis=1)); names.append("X_nAtom")
    for j, lab in enumerate(["N", "F", "O", "S"]):
        cols.append(xn[:, j]); names.append(f"X_{lab}")
    cols.append(np.abs(pa["en"].values - 3.44)); names.append("dEN_AO")
    if onehot:
        for x in XC:
            cols.append((df.X.values == x).astype(float)); names.append(f"X_is_{x}")
        for s in ELEMS:
            cols.append((df.A.values == s).astype(float)); names.append(f"A_is_{s}")
            cols.append((df.B.values == s).astype(float)); names.append(f"B_is_{s}")
    return np.column_stack(cols).astype(np.float32), names


Xtr, names = feat(tr)
Xva, _ = feat(va)
Xtr_oh, names_oh = feat(tr, True)
Xva_oh, _ = feat(va, True)
gtr = tr[["A", "B"]].astype(str).agg("|".join, axis=1).values
gva = va[["A", "B"]].astype(str).agg("|".join, axis=1).values
print(f"特征: 描述符 {Xtr.shape[1]} 维 | 描述符+one-hot {Xtr_oh.shape[1]} 维")
print(f"训练 {len(tr)} 行 / 验证 {len(va)} 行 | 训练集 (A,B) 组数 {len(set(gtr))} / 验证 {len(set(gva))} | 两组重叠 {len(set(gtr) & set(gva))}")

MK = dict(max_iter=600, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=20,
          l2_regularization=1.0, random_state=0)


def Vof(ef, gp, vb, cb):
    p = lambda v: np.square(np.maximum(0, np.divide(v, 0.5, dtype=np.float64)))
    return p(ef - 0.21) + p(1.4 - gp) + p(gp - 3.1) + p(5.73 - vb) + p(cb - 4.50)


metrics = []
t0 = time.time()

# ---------- 1) 直接回归 V：三种模型 × 两套特征 ----------
for tag, A_, B_ in [("描述符", Xtr, Xva), ("描述符+one-hot", Xtr_oh, Xva_oh)]:
    for mname, m in [("HistGB", HistGradientBoostingRegressor(**MK)),
                     ("RF", RandomForestRegressor(n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=0)),
                     ("Ridge", make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-3, 3, 13))))]:
        m.fit(A_, tr.V.values)
        p = m.predict(B_)
        metrics.append(dict(task="V_direct", feat=tag, model=mname,
                            R2=round(r2_score(va.V, p), 4), MAE=round(mean_absolute_error(va.V, p), 4),
                            spearman=round(spearmanr(va.V, p).correlation, 4)))
        print(f"  V直接 | {tag:12s} | {mname:7s} R²={metrics[-1]['R2']:.4f} MAE={metrics[-1]['MAE']:.3f}")

# ---------- 2) 多任务物理量 + 两阶段 gap ----------
preds_val, preds_tr = {}, {}
for col in ["e_form", "vbm", "cbm", "a_lat", "volume"]:
    m = HistGradientBoostingRegressor(**MK).fit(Xtr, tr[col].values)
    preds_val[col] = m.predict(Xva)
    preds_tr[col] = m.predict(Xtr)
    metrics.append(dict(task=col, feat="描述符", model="HistGB",
                        R2=round(r2_score(va[col], preds_val[col]), 4),
                        MAE=round(mean_absolute_error(va[col], preds_val[col]), 4),
                        spearman=round(spearmanr(va[col], preds_val[col]).correlation, 4)))
print(f"  e_form R²={metrics[-5]['R2']:.3f} | vbm {metrics[-4]['R2']:.3f} | cbm {metrics[-3]['R2']:.3f} | a_lat {metrics[-2]['R2']:.3f} | volume {metrics[-1]['R2']:.3f}")

# 单阶段 gap
mg1 = HistGradientBoostingRegressor(**MK).fit(Xtr, tr.gap.values)
g1_val = mg1.predict(Xva)
r2_gap_1 = r2_score(va.gap, g1_val)

# 两阶段
clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=31,
                                     min_samples_leaf=20, l2_regularization=1.0, random_state=0)
clf.fit(Xtr, (tr.gap > 0).astype(int))
pclf = clf.predict_proba(Xva)[:, 1]
sub = (tr.gap > 0).values
mg = HistGradientBoostingRegressor(**MK).fit(Xtr[sub], tr.gap.values[sub])
gap2_val = pclf * mg.predict(Xva)
r2_gap_2 = r2_score(va.gap, gap2_val)
from sklearn.metrics import roc_auc_score
auc = roc_auc_score((va.gap > 0).astype(int), pclf)
metrics += [dict(task="gap", feat="描述符", model="单阶段回归", R2=round(r2_gap_1, 4),
                 MAE=round(mean_absolute_error(va.gap, g1_val), 4), spearman=""),
            dict(task="gap", feat="描述符", model="两阶段(分类×回归)", R2=round(r2_gap_2, 4),
                 MAE=round(mean_absolute_error(va.gap, gap2_val), 4), spearman=f"AUC={auc:.3f}")]
print(f"  gap 单阶段 R²={r2_gap_1:.3f} → 两阶段 R²={r2_gap_2:.3f}（AUC {auc:.3f}）")

pB_val = Vof(preds_val["e_form"], gap2_val, preds_val["vbm"], preds_val["cbm"])
pB_tr = Vof(preds_tr["e_form"], mg1.predict(Xtr), preds_tr["vbm"], preds_tr["cbm"])
metrics.append(dict(task="V_via_physics", feat="描述符", model="物理量→公式",
                    R2=round(r2_score(va.V, pB_val), 4), MAE=round(mean_absolute_error(va.V, pB_val), 4),
                    spearman=round(spearmanr(va.V, pB_val).correlation, 4)))
print(f"  V 物理量路线 R²={metrics[-1]['R2']:.4f} MAE={metrics[-1]['MAE']:.3f} Spearman={metrics[-1]['spearman']:.3f}")

# Top-k 命中
for k in [20, 50, 100]:
    hit_B = len(set(np.argsort(va.V.values)[:k]) & set(np.argsort(pB_val)[:k]))
    print(f"  Top-{k}: {hit_B}/{k}")

# ---------- 3) 不确定性（5 折 bagging 在训练集上，按 (A,B) 分组） ----------
gkf = GroupKFold(n_splits=5)
stds = []
for tri, _ in gkf.split(Xtr, tr.V.values, groups=gtr):
    mb = HistGradientBoostingRegressor(**MK).fit(Xtr[tri], tr.V.values[tri])
    stds.append(mb.predict(Xva))
std_val = np.std(np.vstack(stds), axis=0)
print(f"  不确定性：验证集预测标准差 中位 {np.median(std_val):.2f}，均值 {std_val.mean():.2f}")

# ---------- 4) 出图 ----------
fig, ax = plt.subplots(figsize=(6, 3.6))
ax.hist(np.log10(tr.V.values + 1e-3), bins=80, color="#2E7D8F")
ax.set_xlabel("log10(V + 0.001)"); ax.set_ylabel("样本数")
ax.set_title("图 1  目标违反度 V 的分布（训练集 11,256 条，V=0 的正例为 0 条）")
ax.axvline(np.log10(1 + 1e-3), color="#C0392B", ls="--", lw=1, label="V = 1")
ax.legend(); fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig1_V_dist.png"), dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(5.2, 5))
ax.scatter(va.V.values, pB_val, s=6, alpha=.35, color="#2E7D8F")
lim = [0, 60]; ax.plot(lim, lim, "k--", lw=1)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("真实 V"); ax.set_ylabel("预测 V*")
ax.set_title(f"图 2  验证集预测 vs 真实（R²={metrics[-1]['R2']:.3f}，MAE={metrics[-1]['MAE']:.2f}）")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig2_pred_vs_true.png"), dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 3.4))
ax.hist(va.V.values - pB_val, bins=80, color="#8E7CC3")
ax.set_xlabel("残差（真实 − 预测）"); ax.set_ylabel("样本数"); ax.set_title("图 3  V 预测残差分布")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig3_residual.png"), dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(5.6, 3.2))
ax.bar(["单阶段回归", "两阶段（分类×回归）"], [r2_gap_1, r2_gap_2], color=["#B0BEC5", "#2E7D8F"])
ax.set_ylabel("gap 的验证 R²"); ax.set_ylim(0, 0.6)
for i, v in enumerate([r2_gap_1, r2_gap_2]):
    ax.text(i, v + .01, f"{v:.3f}", ha="center")
ax.set_title(f"图 4  gap 两阶段处理的效果（分类器 AUC={auc:.3f}）")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig4_gap_stage.png"), dpi=200); plt.close(fig)

# 特征重要性（置换重要性，取 V 直接回归模型）
from sklearn.inspection import permutation_importance
mperm = HistGradientBoostingRegressor(**MK).fit(Xtr, tr.V.values)
pi = permutation_importance(mperm, Xva, va.V.values, n_repeats=8, random_state=0, n_jobs=-1)
order = np.argsort(pi.importances_mean)[-15:]
fig, ax = plt.subplots(figsize=(6.4, 4.4))
ax.barh([names[i] for i in order], pi.importances_mean[order], color="#2E7D8F")
ax.set_xlabel("置换重要性（对 MAE 的影响）"); ax.set_title("图 5  特征重要性 Top-15")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig5_importance.png"), dpi=200); plt.close(fig)

# ---------- 5) 落盘 ----------
pd.DataFrame(metrics).to_csv(os.path.join(RES, "metrics.csv"), index=False, encoding="utf-8-sig")
json.dump(dict(metrics=metrics,
               gap_single=float(r2_gap_1), gap_two_stage=float(r2_gap_2), gap_auc=float(auc),
               topk={str(k): len(set(np.argsort(va.V.values)[:k]) & set(np.argsort(pB_val)[:k])) for k in [20, 50, 100]},
               unc_median=float(np.median(std_val)), elapsed_sec=round(time.time() - t0, 1)),
          open(os.path.join(RES, "metrics.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

va_out = va[["id", "formula", "A", "B", "X", "V"]].copy()
va_out["V_hat"] = pB_val
va_out["V_hat_std"] = std_val
va_out["gap_hat"] = gap2_val
va_out.sort_values("V_hat").to_csv(os.path.join(RES, "val_predictions.csv"), index=False, encoding="utf-8-sig")
print(f"\n完成，用时 {time.time()-t0:.0f}s；结果在 {RES}，图在 {FIG}")
print(pd.DataFrame(metrics).to_string(index=False))
