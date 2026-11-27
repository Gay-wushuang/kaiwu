import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(r"e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution")
WORK = Path(r"C:\Users\ERE.DESKTOP-JD48OPB\AppData\Local\Temp\apmcm_repro_original_20261127")
sys.path.insert(0, str(ROOT / "code"))

m = joblib.load(ROOT / "models" / "surrogate_phys.joblib")
P = m["P"]
XCOMP = {"O3": (0, 0, 3, 0), "NO2": (1, 0, 2, 0), "FO2": (0, 1, 2, 0),
         "N2O": (2, 0, 1, 0), "N3": (3, 0, 0, 0), "O2S": (0, 0, 2, 1), "FNO": (0, 1, 1, 1)}
K = ["Z", "group", "period", "en", "rad", "vol", "mass"]


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


def pred_props(df):
    Xp = feat(df)
    r, c, g = m["reg"], m["clf"], m["greg"]
    gp = c.predict_proba(Xp)[:, 1] * g.predict(Xp)
    return pd.DataFrame(dict(ef=r["e_form"].predict(Xp), gap=gp,
                             vbm=r["vbm"].predict(Xp), cbm=r["cbm"].predict(Xp)))


def margins(p):
    return pd.DataFrame(dict(
        m_ef=0.21 - p.ef,
        m_gap_lo=p.gap - 1.4,
        m_gap_hi=3.1 - p.gap,
        m_vbm=5.73 - p.vbm,
        m_cbm=p.cbm - 4.50,
    ))


def V_of(p):
    q = lambda v: np.square(np.maximum(0, v / 0.5))
    return q(p.ef - 0.21) + q(1.4 - p.gap) + q(p.gap - 3.1) + q(5.73 - p.vbm) + q(p.cbm - 4.50)


def load(path):
    return pd.read_csv(path)


print("=" * 72)
print("Q2 全池：V_hat=0 的并列最优")
q2 = load(ROOT / "code/predictions/pool_q2_phys.csv")
q2r = load(WORK / "code/predictions/pool_q2_phys.csv")
for name, df in (("repo", q2), ("repro", q2r)):
    z = df[df.V_hat == 0.0]
    print(f"{name}: 行数={len(df)} | V_hat==0 精确并列={len(z)} | V_hat<1={int((df.V_hat<1).sum())} | min={df.V_hat.min()}")
print("repo 中 V_hat==0 的候选：")
print(q2[q2.V_hat == 0.0][["formula", "A", "B", "X", "V_hat"]].to_string(index=False))

print("\n" + "=" * 72)
print("Q2：LaHfO2N / LaZrO2N 逐项")
for pat in ("LaHfO2N", "LaZrO2N", "Hf", "Zr"):
    hit = q2[q2.formula.astype(str).str.replace("-", "").str.contains(pat, regex=False)]
    print(f"formula 含 {pat}: {len(hit)} 行")
    if 0 < len(hit) <= 8:
        print(hit[["formula", "A", "B", "X", "V_hat"]].to_string(index=False))

for label, df in (("repo", q2), ("repro", q2r)):
    df = df.copy(); df["rank"] = df.V_hat.rank(method="min").astype(int)
    for f in ("La-Hf-O2N", "La-Zr-O2N", "LaHfO2N", "LaZrO2N"):
        hit = df[df.formula.astype(str) == f]
        if len(hit):
            print(f"{label} {f}: V_hat={hit.V_hat.iloc[0]:.9f} rank={hit['rank'].iloc[0]}")

# 属性与余量
cand = q2[(q2.V_hat == 0.0) | q2.formula.astype(str).str.replace("-", "").isin(["LaHfO2N", "LaZrO2N"])].copy()
p = pred_props(cand)
mg = margins(p)
cand = pd.concat([cand.reset_index(drop=True), p, mg], axis=1)
cand["V_recalc"] = V_of(p)
cand["min_margin"] = mg.min(axis=1)
cand["binding"] = mg.idxmin(axis=1)
print("\n候选物理属性与约束余量（负值=违反，0=贴边）：")
print(cand[["formula", "V_hat", "V_recalc", "ef", "gap", "vbm", "cbm"]].to_string(index=False))
print("\n余量：")
print(cand[["formula", "m_ef", "m_gap_lo", "m_gap_hi", "m_vbm", "m_cbm", "min_margin", "binding"]]
      .to_string(index=False))

print("\n" + "=" * 72)
print("Q3 全池：V_hat=0 的并列最优")
q3 = load(ROOT / "code/predictions/pool_q3_phys.csv")
q3r = load(WORK / "code/predictions/pool_q3_phys.csv")
for name, df in (("repo", q3), ("repro", q3r)):
    z = df[df.V_hat == 0.0]
    print(f"{name}: 行数={len(df)} | V_hat==0 精确并列={len(z)} | V_hat<1={int((df.V_hat<1).sum())} | min={df.V_hat.min()}")
print("repo 中 V_hat==0 的候选（前 30）：")
print(q3[q3.V_hat == 0.0][["formula", "A", "B", "X", "V_hat"]].head(30).to_string(index=False))

# 真值标签（仅诊断，不作为泛化证据）
tr = pd.read_csv(ROOT / "date/02_castelli_train.csv")
va = pd.read_csv(ROOT / "date/03_castelli_val.csv")
lab = pd.concat([tr, va], ignore_index=True)[["A", "B", "X", "V"]]
for name, df in (("Q2", q2), ("Q3", q3)):
    mm = df.merge(lab, on=["A", "B", "X"], how="left")
    seen = mm.V.notna()
    print(f"\n{name}: 池中 {len(mm)} 行，02+03 已有标签 {int(seen.sum())} 行 ({seen.mean():.1%})")
    if seen.any():
        print(f"  已见标签 V: min={mm.loc[seen,'V'].min():.3f} median={mm.loc[seen,'V'].median():.3f} max={mm.loc[seen,'V'].max():.3f}")
    for f in ("La-Hf-O2N", "La-Zr-O2N"):
        hit = mm[mm.formula.astype(str) == f]
        if len(hit):
            print(f"  {f}: V_true={hit.V.iloc[0]} V_hat={hit.V_hat.iloc[0]:.6f}")

print("\n" + "=" * 72)
print("Top-20 集合稳定性（不同预测版本；非随机种子实验）")
variants_q2 = {
    "phys_repo": ROOT / "code/predictions/pool_q2_phys.csv",
    "phys_repro": WORK / "code/predictions/pool_q2_phys.csv",
    "histgb": ROOT / "code/predictions/pool_q2.csv",
    "final_v1": ROOT / "code/predictions/pool_q2_final.csv",
}
variants_q3 = {
    "phys_repo": ROOT / "code/predictions/pool_q3_phys.csv",
    "phys_repro": WORK / "code/predictions/pool_q3_phys.csv",
    "histgb": ROOT / "code/predictions/pool_q3.csv",
    "final_v1": ROOT / "code/predictions/pool_q3_final.csv",
}


def top_set(path, k=20):
    df = pd.read_csv(path).sort_values("V_hat")
    return set(df.head(k).formula.astype(str))


for qname, variants in (("Q2", variants_q2), ("Q3", variants_q3)):
    present = {k: v for k, v in variants.items() if v.is_file()}
    print(f"\n{qname}: 可用版本 {list(present)}")
    base = top_set(present["phys_repo"])
    for k, pth in present.items():
        s = top_set(pth)
        jac = len(base & s) / len(base | s) if base | s else 1.0
        print(f"  vs {k}: 交集 {len(base & s)}/20 | Jaccard={jac:.3f}")

print("\n" + "=" * 72)
print("低 V 区域误差（现有 val_predictions.csv，来源需核对其训练脚本）")
vp = load(ROOT / "results/val_predictions.csv")
print("列:", list(vp.columns), "行数:", len(vp))
for q in (0.05, 0.10, 0.20):
    thr = vp.V.quantile(q)
    sub = vp[vp.V <= thr]
    mae = float((sub.V - sub.V_hat).abs().mean())
    rmse = float(np.sqrt(((sub.V - sub.V_hat) ** 2).mean()))
    print(f"  V <= 分位 {q:.0%} (阈值 {thr:.4f}, n={len(sub)}): MAE={mae:.4f} RMSE={rmse:.4f}")
print(f"  全验证集: MAE={float((vp.V-vp.V_hat).abs().mean()):.4f} "
      f"RMSE={float(np.sqrt(((vp.V-vp.V_hat)**2).mean())):.4f} "
      f"R2={float(1-((vp.V-vp.V_hat)**2).sum()/((vp.V-vp.V.mean())**2).sum()):.4f}")
