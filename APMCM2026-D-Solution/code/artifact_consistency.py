"""模型产物与池预测文件的一致性检查（只读，不训练、不覆盖）。

用途：仓库中的 ``models/*.joblib`` 可能被独立复现产物替换，而 ``code/predictions/``
仍是原始预测。两者不是同一批次时，任何“用仓库模型复现预测”的声明都不可信。
本模块只计算差异并返回状态，由 verify_project.py 记为 WARN/BLOCKED。
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from paths import MODELS, PRED, ROOT

K = ["Z", "group", "period", "en", "rad", "vol", "mass"]
XCOMP = {"O3": (0, 0, 3, 0), "NO2": (1, 0, 2, 0), "FO2": (0, 1, 2, 0),
         "N2O": (2, 0, 1, 0), "N3": (3, 0, 0, 0), "O2S": (0, 0, 2, 1), "FNO": (0, 1, 1, 1)}


def feat(df: pd.DataFrame, P: pd.DataFrame) -> np.ndarray:
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


def predict_vhat(model: dict, df: pd.DataFrame) -> np.ndarray:
    Xp = feat(df, model["P"])
    r, c, g = model["reg"], model["clf"], model["greg"]
    gp = c.predict_proba(Xp)[:, 1] * g.predict(Xp)
    q = lambda v: np.square(np.maximum(0, v / 0.5))
    return (q(r["e_form"].predict(Xp) - 0.21) + q(1.4 - gp) + q(gp - 3.1)
            + q(5.73 - r["vbm"].predict(Xp)) + q(r["cbm"].predict(Xp) - 4.50))


def diff_stats(expected, actual, tol: float = 1e-9) -> dict:
    a = np.asarray(expected, dtype=float)
    b = np.asarray(actual, dtype=float)
    if a.shape != b.shape:
        return {"status": "SHAPE_MISMATCH", "expected_shape": list(a.shape),
                "actual_shape": list(b.shape)}
    d = np.abs(a - b)
    return {"status": "OK" if d.max() <= tol else "MISMATCH",
            "n": int(d.size), "max_abs": float(d.max()), "mean_abs": float(d.mean()),
            "exact": int(np.sum(d == 0))}


def compare_model_pool(model_path: Path = None, pool_path: Path = None,
                       tol: float = 1e-4) -> dict:
    """比较模型推理与池文件 V_hat。

    默认容差 1e-4：同批次也会因 float32 特征/CSV 往返产生 ~1e-5 的差；
    不同批次的差异通常远大于该值（当前仓库为 4.7）。
    """
    model_path = Path(model_path or (MODELS / "surrogate_phys.joblib"))
    pool_path = Path(pool_path or (PRED / "pool_q2_phys.csv"))
    if not model_path.is_file() or not pool_path.is_file():
        return {"status": "MISSING", "model": str(model_path), "pool": str(pool_path)}
    model = joblib.load(model_path)
    df = pd.read_csv(pool_path)
    pred = predict_vhat(model, df)
    stats = diff_stats(df.V_hat.values, pred, tol=tol)
    stats.update({"model": str(model_path), "pool": str(pool_path),
                  "model_sha256": _sha(model_path), "pool_sha256": _sha(pool_path),
                  "tolerance": tol})
    return stats


def _sha(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    stats = compare_model_pool()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0 if stats.get("status") == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
