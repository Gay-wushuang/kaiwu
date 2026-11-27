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
    m = joblib.load(model_path)
    P = m["P"]

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
        out["V_hat"] = q(out.ef - 0.21) + q(1.4 - out.gap) + q(out.gap - 3.1) + q(5.73 - out.vbm) + q(out.cbm - 4.50)
        return out
    return pred


print("=" * 74)
print("1. 仓库模型 vs 仓库池文件：是否同一批次")
for tag, model_path, pool_path in (
    ("repo", ROOT / "models/surrogate_phys.joblib", ROOT / "code/predictions/pool_q2_phys.csv"),
    ("repro", WORK / "models/surrogate_phys.joblib", WORK / "code/predictions/pool_q2_phys.csv"),
):
    if not Path(model_path).is_file():
        print(tag, "模型缺失", model_path); continue
    pred = setup(model_path)
    df = pd.read_csv(pool_path)
    p = pred(df)
    d = p.V_hat.values - df.V_hat.values
    print(f"{tag}: max|ΔV|={np.abs(d).max():.6g} mean|ΔV|={np.abs(d).mean():.6g} "
          f"| 完全一致 {int(np.sum(d == 0))}/{len(d)}")

print("\n" + "=" * 74)
print("2. 正确方向的约束余量（全部 >=0 才算可行）")
for tag, model_path, pool_path in (
    ("repo模型+repo池", ROOT / "models/surrogate_phys.joblib", ROOT / "code/predictions/pool_q2_phys.csv"),
    ("repro模型+repro池", WORK / "models/surrogate_phys.joblib", WORK / "code/predictions/pool_q2_phys.csv"),
):
    pred = setup(model_path)
    df = pd.read_csv(pool_path)
    p = pred(df)
    df = pd.concat([df.reset_index(drop=True), p], axis=1)
    df["m_ef"] = 0.21 - df.ef
    df["m_gap_lo"] = df.gap - 1.4
    df["m_gap_hi"] = 3.1 - df.gap
    df["m_vbm"] = df.vbm - 5.73
    df["m_cbm"] = 4.50 - df.cbm
    df["min_margin"] = df[["m_ef", "m_gap_lo", "m_gap_hi", "m_vbm", "m_cbm"]].min(axis=1)
    sel = df[df.formula.isin(["LaHfO2N", "LaZrO2N"])]
    print(f"\n{tag}:")
    print(sel[["formula", "V_hat", "ef", "gap", "vbm", "cbm"]].to_string(index=False))
    print(sel[["formula", "m_ef", "m_gap_lo", "m_gap_hi", "m_vbm", "m_cbm", "min_margin"]].to_string(index=False))

print("\n" + "=" * 74)
print("3. 两个候选的真值标签（仅诊断；已见标签不作泛化证据）")
tr = pd.read_csv(ROOT / "date/02_castelli_train.csv")
va = pd.read_csv(ROOT / "date/03_castelli_val.csv")
lab = pd.concat([tr, va], ignore_index=True)
for f in ("LaHfO2N", "LaZrO2N"):
    parts = None
    for _, r in lab.iterrows():
        if str(r.formula).replace("-", "") == f:
            parts = r; break
    print(f, "V_true =", None if parts is None else parts.V, "| 来源行:",
          None if parts is None else f"{parts.get('id')} A={parts.A} B={parts.B} X={parts.X}")

print("\n" + "=" * 74)
print("4. Q2/Q3 V_hat=0 并列候选的约束余量（与池文件同批次）")
for q, pool_name in (("Q2", "pool_q2_phys.csv"), ("Q3", "pool_q3_phys.csv")):
    pred = setup(ROOT / "models/surrogate_phys.joblib")
    df = pd.read_csv(ROOT / "code/predictions" / pool_name)
    p = pred(df)
    df = pd.concat([df.reset_index(drop=True), p], axis=1)
    df["m_ef"] = 0.21 - df.ef
    df["m_gap_lo"] = df.gap - 1.4
    df["m_gap_hi"] = 3.1 - df.gap
    df["m_vbm"] = df.vbm - 5.73
    df["m_cbm"] = 4.50 - df.cbm
    df["min_margin"] = df[["m_ef", "m_gap_lo", "m_gap_hi", "m_vbm", "m_cbm"]].min(axis=1)
    z = df[df.V_hat == 0.0]
    print(f"\n{q}: V_hat==0 共 {len(z)} 个")
    if len(z):
        print(z[["formula", "m_ef", "m_gap_lo", "m_gap_hi", "m_vbm", "m_cbm", "min_margin"]].to_string(index=False))

print("\n" + "=" * 74)
print("5. 文件时间与哈希")
import hashlib
for f in ("models/surrogate_phys.joblib", "code/predictions/pool_q2_phys.csv",
          "code/predictions/pool_q3_phys.csv"):
    p = ROOT / f
    h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    print(f"{f}: mtime={pd.Timestamp(p.stat().st_mtime, unit='s')} sha256={h}… bytes={p.stat().st_size}")
