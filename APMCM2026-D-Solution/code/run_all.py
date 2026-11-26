# -*- coding: utf-8 -*-
"""D 题端到端一键复现：数据核对 → 代理模型 → 三题求解 → 交付物
输出：results/FINAL_ANSWERS.md、results/submission_*.csv、models/*.joblib
"""
import os, json, warnings, time
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from mendeleev import element as mel
from xgboost import XGBRegressor, XGBClassifier
import joblib
import kaiwu as kw
import kaiwu.preprocess as pp

ROOT = r"D:\比赛\APMCM\D题"
DAT, CODE, RES = (os.path.join(ROOT, d) for d in ("date", "code", "results"))
MOD = os.path.join(ROOT, "models")
os.makedirs(MOD, exist_ok=True); os.makedirs(RES, exist_ok=True)
t0 = time.time()
log = []


def say(s=""):
    print(s)
    log.append(s)


# ---------------------------------------------------------------- 1. 数据核对
say("=" * 62)
say("步骤 1  数据核对")
FILES = {"02": "02_castelli_train.csv", "03": "03_castelli_val.csv", "04": "04_castelli_test_holdout.csv",
         "06": "06_castelli_no_physics.csv", "07": "07_castelli_q2_pool.csv", "08": "08_castelli_q3_pool.csv",
         "11": "11_castelli_q2_pool_blind.csv", "12": "12_castelli_q3_pool_blind.csv"}
D = {k: pd.read_csv(os.path.join(DAT, f)) for k, f in FILES.items()}
for k, df in D.items():
    say(f"  {k}: {len(df):>6} 行, {df.shape[1]:>2} 列")
tr, va, ho = D["02"], D["03"], D["04"]
say(f"  候选总数 52×52×7 = {52*52*7:,}；训练+验证 {len(tr)+len(va):,} 行")
if "V" in tr.columns:
    say(f"  训练集 V=0 的记录: {int((tr.V==0).sum())}；验证集: {int((va.V==0).sum())}")
say("  结论：训练与验证中没有任何正例，代理模型必须做成回归。")

# ---------------------------------------------------------------- 2. 代理模型
say()
say("=" * 62)
say("步骤 2  代理模型（35 维元素描述符 + 两阶段 gap + 物理量路线）")
al = pd.concat([tr, va], ignore_index=True)
ELEMS = sorted(set(al.A) | set(al.B))
P = {}
for s in ELEMS:
    e = mel(s)
    P[s] = dict(Z=e.atomic_number, group=e.group_id or 0, period=e.period,
                en=e.electronegativity_pauling() or np.nan, rad=e.atomic_radius or np.nan,
                vol=e.atomic_volume or np.nan, mass=e.mass)
P = pd.DataFrame(P).T
for c in ("en", "rad", "vol"):
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
Xtr, Xva = feat(tr), feat(va)
reg, clf, greg = {}, None, None
for col in ("e_form", "vbm", "cbm"):
    reg[col] = XGBRegressor(**MK).fit(Xtr, tr[col].values)
clf = XGBClassifier(n_estimators=600, learning_rate=0.05, max_depth=5, subsample=0.9,
                    colsample_bytree=0.9, reg_lambda=1.0, n_jobs=-1, random_state=0,
                    tree_method="hist", eval_metric="logloss").fit(Xtr, (tr.gap > 0).astype(int))
sub = (tr.gap > 0).values
greg = XGBRegressor(**MK).fit(Xtr[sub], tr.gap.values[sub])

# 验证（02 训练 → 03 验证）
def predict(df, models):
    Xp = feat(df)
    r_, c_, g_ = models
    return Vof(r_["e_form"].predict(Xp), c_.predict_proba(Xp)[:, 1] * g_.predict(Xp),
               r_["vbm"].predict(Xp), r_["cbm"].predict(Xp))


pv = predict(va, (reg, clf, greg))
y = va.V.values
mae = float(np.abs(pv - y).mean())
rmse = float(np.sqrt(((pv - y) ** 2).mean()))
r2 = float(1 - ((pv - y) ** 2).sum() / ((y - y.mean()) ** 2).sum())
from scipy.stats import spearmanr
rho = float(spearmanr(pv, y).statistic)
top100 = int((np.argsort(pv)[:100] < 0).sum()) if False else int(len(set(np.argsort(pv)[:100]) & set(np.argsort(y)[:100])))
say(f"  验证集（02→03）：R²={r2:.3f}  MAE={mae:.3f}  RMSE={rmse:.3f}  Spearman={rho:.3f}  Top-100 命中={top100}/100")

# 最终模型：02+03 全量重训
Xa = feat(al)
reg = {c: XGBRegressor(**MK).fit(Xa, al[c].values) for c in ("e_form", "vbm", "cbm")}
clf = XGBClassifier(n_estimators=600, learning_rate=0.05, max_depth=5, subsample=0.9,
                    colsample_bytree=0.9, reg_lambda=1.0, n_jobs=-1, random_state=0,
                    tree_method="hist", eval_metric="logloss").fit(Xa, (al.gap > 0).astype(int))
suba = (al.gap > 0).values
greg = XGBRegressor(**MK).fit(Xa[suba], al.gap.values[suba])
joblib.dump({"reg": reg, "clf": clf, "greg": greg, "P": P}, os.path.join(MOD, "surrogate_phys.joblib"))
say(f"  最终模型已保存 models/surrogate_phys.joblib（02+03 共 {len(al):,} 行）")

# ---------------------------------------------------------------- 3. 交付：holdout 与四个池
say()
say("=" * 62)
say("步骤 3  预测与交付文件")
ho2 = ho.assign(V_hat=predict(ho, (reg, clf, greg)))
ho2[["id", "formula", "A", "B", "X", "V_hat"]].to_csv(
    os.path.join(RES, "submission_q1_holdout.csv"), index=False, encoding="utf-8-sig")
say(f"  holdout 3,703 行 → results/submission_q1_holdout.csv（V̂ 最小 {ho2.V_hat.min():.3f}）")

POOLS = {"q2": "07_castelli_q2_pool.csv", "q3": "08_castelli_q3_pool.csv",
         "q2b": "11_castelli_q2_pool_blind.csv", "q3b": "12_castelli_q3_pool_blind.csv"}
pool = {}
for k, f in POOLS.items():
    df = D[k] if k in D else pd.read_csv(os.path.join(DAT, f))
    d2 = df.assign(V_hat=predict(df, (reg, clf, greg))).sort_values("V_hat")
    d2.to_csv(os.path.join(CODE, f"pool_{k}_phys.csv"), index=False, encoding="utf-8-sig")
    pool[k] = d2
    say(f"  {k}: {len(df):>5} 个 | V̂ min {d2.V_hat.min():.4f} | V̂<1 的 {int((d2.V_hat<1).sum()):>3} 个 | 首位 {d2.iloc[0].formula}")

# ---------------------------------------------------------------- 4. 问题 2
say()
say("=" * 62)
say("步骤 4  问题 2（X=NO2）：QUBO + 精确枚举 + 模拟退火")


def build_sub(poolX, topk):
    Vm = poolX.pivot_table(index="A", columns="B", values="V_hat", aggfunc="first")
    A, B, V = list(Vm.index), list(Vm.columns), Vm.values
    if topk:
        ia = np.argsort(V.min(1))[:topk]; ib = np.argsort(V.min(0))[:topk]
        A = [A[i] for i in ia]; B = [B[i] for i in ib]; V = V[np.ix_(ia, ib)]
    return A, B, V


def qubo_of(V, M):
    nA, nB = V.shape
    Q = np.zeros((nA + nB, nA + nB))
    Q[:nA, nA:] = V
    for base, k in ((0, nA), (nA, nB)):
        for i in range(base, base + k):
            Q[i, i] -= M
            for j in range(i + 1, base + k):
                Q[i, j] += 2 * M
    return Q


def solve_block(A, B, V, tag, topk, sa_restarts=400):
    M = max(2 * (V.max() - V.min()), 1) + 15
    Q = qubo_of(V, M)
    I, _ = kw.core.qubo_matrix_to_ising_matrix(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    nA, nB = V.shape
    Ir = np.abs(np.asarray(I, dtype=float))          # 解析口径：用原始 Ising 矩阵算分辨率
    step = Ir.max() / 127
    obj = Ir[:nA, nA:nA + nB].max()
    rng = np.random.default_rng(7)
    best_sa, best_v = None, np.inf
    n = adj.shape[0]
    for _ in range(sa_restarts):
        s = rng.choice([-1.0, 1.0], size=n)
        T, T0, T1, sweeps = 3000.0, 3000.0, 1.0, 400
        alpha = (T1 / T0) ** (1.0 / sweeps)
        for _ in range(sweeps):
            i = rng.integers(n)
            dH = 2 * s[i] * (adj[i] @ s) - 2 * adj[i, i]
            if dH <= 0 or rng.random() < np.exp(-dH / max(T, 1e-9)):
                s[i] = -s[i]
            T *= alpha
        bits = ((s.astype(int) + 1) // 2)[:nA + nB]
        ai = np.flatnonzero(bits[:nA]); bi = np.flatnonzero(bits[nA:])
        if len(ai) == 1 and len(bi) == 1 and V[ai[0], bi[0]] < best_v:
            best_v = V[ai[0], bi[0]]; best_sa = (A[ai[0]], B[bi[0]])
    i0, j0 = np.unravel_index(V.argmin(), V.shape)
    say(f"  {tag}: {V.shape[0]}×{V.shape[1]} | {Q.shape[0]} 比特 | M={M:.0f} | 物体分辨率 {obj/step:.2f} 档")
    i0, j0 = np.unravel_index(V.argmin(), V.shape)
    if best_sa is None:
        say(f"      精确最优 {A[i0]}-{B[j0]} V*={V[i0,j0]:.4f}；退火在 {sa_restarts} 次重启内未找到合法解")
        return dict(tag=tag, bits=int(Q.shape[0]), M=float(M), resol=round(float(obj / step), 2),
                    exact=f"{A[i0]}-{B[j0]}", exact_V=float(V[i0, j0]), sa="未找到合法解", sa_V=None)
    say(f"      精确最优 {A[i0]}-{B[j0]} V*={V[i0,j0]:.4f}；退火最优 {best_sa[0]}-{best_sa[1]} V={best_v:.4f}")
    return dict(tag=tag, bits=int(Q.shape[0]), M=float(M), resol=round(float(obj / step), 2),
                exact=f"{A[i0]}-{B[j0]}", exact_V=float(V[i0, j0]),
                sa=f"{best_sa[0]}-{best_sa[1]}", sa_V=float(best_v))


q2_full = build_sub(pool["q2"], 0)
q2_sub = build_sub(pool["q2"], 13)
say(f"  全量池最优：{q2_full[0][np.argmin(q2_full[2].min(1))]} 侧最小、V* = {q2_full[2].min():.4f}")
r_q2_full = solve_block(*q2_full, "问题2 全量 52×52", 0, sa_restarts=0)
r_q2 = solve_block(*q2_sub, "问题2 预筛 13×13", 13)

# ---------------------------------------------------------------- 5. 问题 3
say()
say("=" * 62)
say("步骤 5  问题 3：固定 X 分三次求解")
r_q3 = []
for X in ("O3", "NO2", "FO2"):
    px = pool["q3"][pool["q3"].X == X]
    A, B, V = build_sub(px, 13)
    r_q3.append(solve_block(A, B, V, f"问题3 X={X} 预筛 13×13", 13, sa_restarts=400))

# ---------------------------------------------------------------- 6. 汇总
say()
say("=" * 62)
say("步骤 6  结论汇总")
best_q2 = pool["q2"].iloc[0]
best_q3 = pool["q3"].iloc[0]
say(f"  问题 2 答案：{best_q2.formula}（A={best_q2.A}, B={best_q2.B}），V̂ = {best_q2.V_hat:.4f}")
say(f"  问题 3 答案：{best_q3.formula}（A={best_q3.A}, B={best_q3.B}, X={best_q3.X}），V̂ = {best_q3.V_hat:.4f}")
for r in r_q3:
    sv = "—" if r["sa_V"] is None else f"{r['sa_V']:.4f}"
    say(f"    {r['tag']}: 精确最优 {r['exact']} V*={r['exact_V']:.4f} | 退火 {r['sa']} V={sv}")
say(f"  全流程耗时 {time.time()-t0:.1f} s")

# 提交文件
pool["q2"].head(20)[["id", "formula", "A", "B", "X", "V_hat"]].to_csv(
    os.path.join(RES, "submission_q2_top20.csv"), index=False, encoding="utf-8-sig")
pool["q3"].head(20)[["id", "formula", "A", "B", "X", "V_hat"]].to_csv(
    os.path.join(RES, "submission_q3_top20.csv"), index=False, encoding="utf-8-sig")

summary = dict(validate=dict(r2=r2, mae=mae, rmse=rmse, spearman=rho, top100=top100),
               q2=dict(best=best_q2.formula, V=float(best_q2.V_hat), num_lt1=int((pool["q2"].V_hat < 1).sum())),
               q3=dict(best=best_q3.formula, X=best_q3.X, V=float(best_q3.V_hat),
                       num_lt1=int((pool["q3"].V_hat < 1).sum())),
               q3_by_X={r["tag"]: dict(exact=r["exact"], V=r["exact_V"]) for r in r_q3},
               q2_blocks=[r_q2_full, r_q2], holdout_min=float(ho2.V_hat.min()),
               runtime_s=round(time.time() - t0, 1))
json.dump(summary, open(os.path.join(RES, "final_answers.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

md = ["# D 题端到端复现结果", "", f"运行时间：{time.strftime('%Y-%m-%d %H:%M')}，耗时 {summary['runtime_s']} s", "",
      "## 代理模型（02 训练 / 03 验证）", "",
      f"| R² | MAE | RMSE | Spearman | Top-100 命中 |", "|---|---|---|---|---|",
      f"| {r2:.3f} | {mae:.3f} | {rmse:.3f} | {rho:.3f} | {top100}/100 |", "",
      "## 问题 2（X = NO₂）", "", f"**答案：{best_q2.formula}，V̂ = {best_q2.V_hat:.4f}**", "",
      "| 配置 | 比特 | 罚项 M | 目标分辨率 | 精确最优 | 退火最优 |", "|---|---|---|---|---|---|"]
for r in [r_q2_full, r_q2]:
    sv = "—" if r['sa_V'] is None else f"{r['sa_V']:.4f}"
    md.append(f"| {r['tag']} | {r['bits']} | {r['M']:.0f} | {r['resol']:.2f} 档 | {r['exact']} ({r['exact_V']:.4f}) | {r['sa']} ({sv}) |")
md += ["", "## 问题 3（X ∈ {O₃, NO₂, FO₂}）", "", f"**答案：{best_q3.formula}（X = {best_q3.X}），V̂ = {best_q3.V_hat:.4f}**", "",
       "| 固定 X | 比特 | 罚项 M | 精确最优 | 退火最优 |", "|---|---|---|---|---|"]
for r in r_q3:
    sv = "—" if r['sa_V'] is None else f"{r['sa_V']:.4f}"
    md.append(f"| {r['tag'].split('X=')[1].split()[0]} | {r['bits']} | {r['M']:.0f} | {r['exact']} ({r['exact_V']:.4f}) | {r['sa']} ({sv}) |")
md += ["", "## 交付文件", "", "| 文件 | 内容 |", "|---|---|",
       "| `results/submission_q1_holdout.csv` | 3,703 行 holdout 的预测 V̂ |",
       "| `results/submission_q2_top20.csv` | 问题 2 前 20 候选 |",
       "| `results/submission_q3_top20.csv` | 问题 3 前 20 候选 |",
       "| `results/final_answers.json` | 全部数值的机器可读版本 |",
       "| `models/surrogate_phys.joblib` | 训练好的代理模型 |", "",
       "> 真机实验（3 次配额已用完）的结果见 `results/cim_stats/` 与 `results/vendor_reports/`。"]
open(os.path.join(RES, "FINAL_ANSWERS.md"), "w", encoding="utf-8").write("\n".join(md))
open(os.path.join(RES, "run_all.log"), "w", encoding="utf-8").write("\n".join(log))
say()
say("已写 results/FINAL_ANSWERS.md · final_answers.json · run_all.log")
