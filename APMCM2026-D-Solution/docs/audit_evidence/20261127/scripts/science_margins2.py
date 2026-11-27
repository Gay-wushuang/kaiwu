import hashlib
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(r"e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution")
WORK = Path(r"C:\Users\ERE.DESKTOP-JD48OPB\AppData\Local\Temp\apmcm_repro_original_20261127")
sys.path.insert(0, str(ROOT / "code"))
XCOMP = {"O3": (0, 0, 3, 0), "NO2": (1, 0, 2, 0), "FO2": (0, 1, 2, 0),
         "N2O": (2, 0, 1, 0), "N3": (3, 0, 0, 0), "O2S": (0, 0, 2, 1), "FNO": (0, 1, 1, 1)}
K = ["Z", "group", "period", "en", "rad", "vol", "mass"]


def setup(model_path):
    m = joblib.load(model_path); P = m["P"]

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

    def pred(df):
        Xp = feat(df)
        r, c, g = m["reg"], m["clf"], m["greg"]
        gp = c.predict_proba(Xp)[:, 1] * g.predict(Xp)
        out = pd.DataFrame(dict(ef=r["e_form"].predict(Xp), gap=gp,
                                vbm=r["vbm"].predict(Xp), cbm=r["cbm"].predict(Xp)))
        q = lambda v: np.square(np.maximum(0, v / 0.5))
        out["V_pred"] = q(out.ef - 0.21) + q(1.4 - out.gap) + q(out.gap - 3.1) + q(5.73 - out.vbm) + q(out.cbm - 4.50)
        return out
    return pred


def add_margins(df, p):
    d = pd.concat([df.reset_index(drop=True), p.reset_index(drop=True)], axis=1)
    d["m_ef"] = 0.21 - d.ef
    d["m_gap_lo"] = d.gap - 1.4
    d["m_gap_hi"] = 3.1 - d.gap
    d["m_vbm"] = d.vbm - 5.73
    d["m_cbm"] = 4.50 - d.cbm
    d["min_margin"] = d[["m_ef", "m_gap_lo", "m_gap_hi", "m_vbm", "m_cbm"]].min(axis=1)
    d["binding"] = d[["m_ef", "m_gap_lo", "m_gap_hi", "m_vbm", "m_cbm"]].idxmin(axis=1)
    return d


print("=" * 76)
print("1. 批次一致性：仓库模型 vs 仓库池；复现模型 vs 复现池")
for tag, mp, pp in (("repo", ROOT / "models/surrogate_phys.joblib", ROOT / "code/predictions/pool_q2_phys.csv"),
                    ("repro", WORK / "models/surrogate_phys.joblib", WORK / "code/predictions/pool_q2_phys.csv")):
    pred = setup(mp); df = pd.read_csv(pp); p = pred(df)
    d = p.V_pred.values - df.V_hat.values
    print(f"{tag}: max|ΔV|={np.abs(d).max():.6g} mean|ΔV|={np.abs(d).mean():.6g} exact={int(np.sum(np.abs(d)<1e-9))}/{len(d)}")
    if tag == "repo":
        sp = pd.Series(df.V_hat.values).corr(pd.Series(p.V_pred.values), method="spearman")
        print(f"  repo 池 V_hat vs 当前模型 V_pred: Spearman={sp:.6f}")

print("\n" + "=" * 76)
print("2. Q2/Q3：V_hat==0（池文件）候选的物理余量与真值标签")
tr = pd.read_csv(ROOT / "date/02_castelli_train.csv")
va = pd.read_csv(ROOT / "date/03_castelli_val.csv")
lab = pd.concat([tr, va], ignore_index=True)[["A", "B", "X", "V"]]
for q, name in (("Q2", "pool_q2_phys.csv"), ("Q3", "pool_q3_phys.csv")):
    pred = setup(ROOT / "models/surrogate_phys.joblib")
    df = pd.read_csv(ROOT / "code/predictions" / name)
    p = pred(df)
    d = add_margins(df, p)
    z = d[d.V_hat == 0.0].copy()
    z = z.merge(lab, on=["A", "B", "X"], how="left")
    print(f"\n{q}: 池 {len(d)} | V_hat==0 {len(z)} | 其中有真值 {int(z.V.notna().sum())}")
    if len(z):
        print(z[["formula", "m_ef", "m_gap_lo", "m_gap_hi", "m_vbm", "m_cbm", "min_margin", "binding", "V"]]
              .to_string(index=False))
    top20 = d.nsmallest(20, "V_hat").merge(lab, on=["A", "B", "X"], how="left")
    print(f"  Top-20 中有真值标签 {int(top20.V.notna().sum())}/20；真值 V 范围 "
          f"[{top20.V.min()}, {top20.V.max()}]")

print("\n" + "=" * 76)
print("3. LaHfO2N / LaZrO2N：池值、当前模型值、真值、余量")
pred = setup(ROOT / "models/surrogate_phys.joblib")
q2 = pd.read_csv(ROOT / "code/predictions/pool_q2_phys.csv")
d = add_margins(q2, pred(q2)).merge(lab, on=["A", "B", "X"], how="left")
sel = d[d.formula.isin(["LaHfO2N", "LaZrO2N"])]
print(sel[["formula", "V_hat", "V_pred", "V", "m_ef", "m_gap_lo", "m_gap_hi", "m_vbm", "m_cbm", "min_margin"]]
      .to_string(index=False))
print("\n说明：V_hat 为仓库池文件值（历史模型）；V_pred 为仓库 joblib 当前推理值；V 为 02/03 已见标签，仅诊断。")

print("\n" + "=" * 76)
print("4. 池子与已见标签的重叠（Q2/Q3）")
for q, name in (("Q2", "pool_q2_phys.csv"), ("Q3", "pool_q3_phys.csv")):
    df = pd.read_csv(ROOT / "code/predictions" / name)
    mm = df.merge(lab, on=["A", "B", "X"], how="left")
    seen = mm.V.notna()
    print(f"{q}: {len(mm)} 行 | 已见 {int(seen.sum())} ({seen.mean():.1%}) | 未见 {int((~seen).sum())}")
    if seen.any():
        print(f"  已见标签 V: min={mm.loc[seen,'V'].min():.3f} median={mm.loc[seen,'V'].median():.3f} "
              f"V<=1 的 {int((mm.loc[seen,'V']<=1).sum())} 个")

print("\n" + "=" * 76)
print("5. 文件时间与哈希")
for f in ("models/surrogate_phys.joblib", "code/predictions/pool_q2_phys.csv",
          "code/predictions/pool_q3_phys.csv", "results/final_answers.json"):
    p = ROOT / f
    print(f"{f}: mtime={pd.Timestamp(p.stat().st_mtime, unit='s')} "
          f"sha256={hashlib.sha256(p.read_bytes()).hexdigest()[:16]}… bytes={p.stat().st_size}")
