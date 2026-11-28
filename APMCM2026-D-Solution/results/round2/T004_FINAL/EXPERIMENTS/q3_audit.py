# -*- coding: utf-8 -*-
"""T004-01/02：Q3 证据机械核查（不提交真机、不消耗配额）。

只复算归档与预测文件，不改动任何历史证据。
输出：q3_audit.json（同目录）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]          # APMCM2026-D-Solution
CODE = ROOT / "code"
sys.path.insert(0, str(CODE))

import d_submit_cim as S                            # noqa: E402
import kaiwu as kw                                  # noqa: E402
import kaiwu.preprocess as pp                       # noqa: E402
from experiment_input import matrix_sha256, numeric_matrix_sha256  # noqa: E402

TASKS = ROOT / "experiments" / "tasks"
PRED = ROOT / "code" / "predictions"
OUT = Path(__file__).resolve().parent / "q3_audit.json"

ARCHIVE = {
    "O3": TASKS / "t20261128-003159-b_q3_o3_baseline-7cd9ce6b",
    # NO2 切片与 Q2 基线任务使用同一输入矩阵（hash 0001ed…），复用该任务，不重复计为独立实验
    "NO2": TASKS / "t20261128-003014-b_q2_baseline-be06017f",
    "FO2": TASKS / "t20261128-003216-b_q3_fo2_baseline-ca295ce6",
}


def load_matrix_csv(path):
    df = pd.read_csv(path, index_col=0)
    return [str(x) for x in df.index], [str(x) for x in df.columns], df.to_numpy(float)


def legal_energies(V, I, nA, nB):
    """枚举全部合法 one-hot 指派；aux 取使其能量最小的符号。"""
    n = nA + nB
    out = []
    for i in range(nA):
        for j in range(nB):
            s = -np.ones(n + 1)
            s[i] = 1
            s[nA + j] = 1
            hs = []
            for a in (-1, 1):
                s[-1] = a
                hs.append(float(-s @ I @ s))
            out.append((i, j, float(V[i, j]), min(hs)))
    return out


def exact_submitted_space(adj, nA=13, nB=13):
    """对实际提交的 (nA+nB+1) 自旋 Ising 做全空间精确枚举。

    利用 QUBO 结构：组内非对角系数一致、A-B 交叉块非负。
    对每个 A/B 子集组合计算 aux=+1 与 aux=-1 的较小能量。
    """
    n = nA + nB
    Qp, offp = kw.core.ising_matrix_to_qubo_matrix(adj)
    Qp = np.asarray(Qp, float)
    assert Qp.shape == (n, n)
    d = np.diag(Qp)
    off_a = Qp[0, 1]
    off_b = Qp[nA, nA + 1]
    assert np.allclose(Qp[np.triu_indices(nA, 1)], off_a)
    assert np.allclose(Qp[nA + np.triu_indices(nB, 1)[0], nA + np.triu_indices(nB, 1)[1]], off_b)
    C = Qp[:nA, nA:]
    j = adj[:n, n]

    X = ((np.arange(1 << nA)[:, None] >> np.arange(nA)[None, :]) & 1).astype(np.float64)
    Y = ((np.arange(1 << nB)[:, None] >> np.arange(nB)[None, :]) & 1).astype(np.float64)
    kA = X.sum(1)
    kB = Y.sum(1)
    linA = X @ d[:nA]
    linB = Y @ d[nA:]
    # j^T s = 2*sum_{selected} j - sum_all j
    uA = X @ j[:nA]
    uB = Y @ j[nA:]
    jsum = float(j.sum())
    # kaiwu 的 QUBO 以上三角存储为准：x^T Q x 的组内交叉项为 off*C(k,2)
    penA = off_a * kA * (kA - 1) / 2.0
    penB = off_b * kB * (kB - 1) / 2.0
    CY = (X @ C) @ Y.T

    best_legal = (np.inf, None)
    best_illegal = (np.inf, None)
    best_legal_plus = (np.inf, None)
    best_illegal_plus = (np.inf, None)
    for start in range(0, 1 << nA, 128):
        xs = slice(start, min(start + 128, 1 << nA))
        base = (offp + linA[xs, None] + linB[None, :]
                + penA[xs, None] + penB[None, :] + CY[xs, :])
        u = 2.0 * (uA[xs, None] + uB[None, :]) - jsum
        e = np.minimum(base, base + 4.0 * u)
        kkA = kA[xs, None]
        kkB = kB[None, :]
        legal = (kkA == 1) & (kkB == 1)
        for mask, e_now, plus, is_legal in (
                (legal, e, False, True), (~legal, e, False, False),
                (legal, base, True, True), (~legal, base, True, False)):
            if not np.any(mask):
                continue
            v = float(e_now[mask].min())
            tgt = (best_legal_plus if plus else best_legal) if is_legal \
                else (best_illegal_plus if plus else best_illegal)
            if v < tgt[0]:
                ii, jj = np.nonzero(mask)
                k = int(np.argmin(e_now[mask]))
                tgt = (v, (int(ii[k]) + start, int(jj[k])))
                if plus:
                    if is_legal:
                        best_legal_plus = tgt
                    else:
                        best_illegal_plus = tgt
                else:
                    if is_legal:
                        best_legal = tgt
                    else:
                        best_illegal = tgt
    return dict(
        min_legal_anyaux=best_legal[0], min_legal_anyaux_state=best_legal[1],
        min_illegal_anyaux=best_illegal[0], min_illegal_anyaux_state=best_illegal[1],
        min_legal_aux_plus=best_legal_plus[0], min_legal_aux_plus_state=best_legal_plus[1],
        min_illegal_aux_plus=best_illegal_plus[0], min_illegal_aux_plus_state=best_illegal_plus[1],
        gap_anyaux=best_illegal[0] - best_legal[0],
        gap_aux_plus=best_illegal_plus[0] - best_legal_plus[0],
        ground_state_all_legal_anyaux=bool(best_illegal[0] > best_legal[0]),
        ground_state_contains_legal=bool(best_legal[0] <= best_illegal[0]),
        note="Ising 无外场时 H(s)=H(-s)：任一合法态的全局翻转是非法态且能量相同，"
             "故全空间基态必然同时包含合法与非法态；aux=+1 的二进制域无此对称性。",
        structure=dict(n=n, offdiag_A=float(off_a), offdiag_B=float(off_b),
                       diag_A_min=float(d[:nA].min()), diag_A_max=float(d[:nA].max()),
                       diag_B_min=float(d[nA:].min()), diag_B_max=float(d[nA:].max()),
                       cross_min=float(C.min()), cross_max=float(C.max()),
                       aux_coupling_min=float(j.min()), aux_coupling_max=float(j.max())),
    )


def q3_report(x):
    path = ARCHIVE[x]
    A_in, B_in, V_in = load_matrix_csv(path / "input" / "matrix.csv")
    subm = json.loads((path / "input" / "submitted_mapping.json").read_text(encoding="utf-8"))
    cfg = json.loads((path / "config.json").read_text(encoding="utf-8"))
    task = json.loads((path / "task.json").read_text(encoding="utf-8"))
    V_sub = pd.read_csv(path / "input" / "submitted_target_V.csv", index_col=0).to_numpy(float)

    ia = np.argsort(V_in.min(1))[: cfg["topk"]]
    ib = np.argsort(V_in.min(0))[: cfg["topk"]]
    A_sel = [A_in[k] for k in ia]
    B_sel = [B_in[k] for k in ib]
    V_sel = V_in[np.ix_(ia, ib)]

    vmin = float(V_in.min())
    arg = np.argwhere(V_in <= vmin + 1e-12)
    raw_set = [(A_in[i], B_in[j], float(V_in[i, j])) for i, j in arg]
    raw_pairs = {(a, b) for a, b, _ in raw_set}

    # 实际提交域：重建并逐字核对归档哈希
    Qs, _, _ = S.build_qubo(V_sel)
    Is_, _ = S.to_ising(Qs)
    adj_sub = np.asarray(pp.adjust_ising_matrix_precision(Is_, 8), dtype=float)
    I_raw_arch = np.load(path / "input" / "ising_matrix_raw.npz")["matrix"]
    adj_arch = pd.read_csv(path / "input" / "ising_matrix.csv", header=None).to_numpy(float)

    leg_sub = legal_energies(V_sel, adj_sub, len(A_sel), len(B_sel))
    Hs = np.array([r[3] for r in leg_sub])
    hs_min = float(Hs.min())
    qset_sub = {(A_sel[i], B_sel[j]) for i, j, _, h in leg_sub if abs(h - hs_min) < 1e-9}
    raw_sub_min = float(V_sel.min())
    raw_sub_pairs = {(A_sel[i], B_sel[j]) for i, j, v, _ in leg_sub if abs(v - raw_sub_min) < 1e-12}
    from scipy.stats import spearmanr
    rho_sub = float(spearmanr([r[2] for r in leg_sub], Hs).statistic)

    # 全 52×52 域（仅合法域枚举；不代表实际提交）
    Q_full, _, _ = S.build_qubo(V_in)
    I_full, _ = S.to_ising(Q_full)
    adj_full = np.asarray(pp.adjust_ising_matrix_precision(I_full, 8), dtype=float)
    leg_full = legal_energies(V_in, adj_full, len(A_in), len(B_in))
    Hf = np.array([r[3] for r in leg_full])
    hf_min = float(Hf.min())
    qset_full = {(A_in[i], B_in[j]) for i, j, _, h in leg_full if abs(h - hf_min) < 1e-9}
    rho_full = float(spearmanr([r[2] for r in leg_full], Hf).statistic)
    v_of = {(a, b): float(V_in[i, j]) for i, a in enumerate(A_in) for j, b in enumerate(B_in)}
    qset_full_v = sorted((a, b, v_of[(a, b)]) for a, b in qset_full)
    qset_sub_v = sorted((a, b, v_of[(a, b)]) for a, b in qset_sub)

    space = exact_submitted_space(adj_sub, len(A_sel), len(B_sel))

    # 真机
    sol = np.load(path / "raw" / "solutions.npz")["solutions"]
    energy = pd.read_csv(path / "raw" / "solution_energy.csv")
    hw = []
    nA_s, nB_s = len(A_sel), len(B_sel)
    for k, srow in enumerate(sol):
        s = srow.astype(float)
        H = float(-s @ adj_arch @ s)
        bits = ((s + 1) // 2).astype(int)[: nA_s + nB_s]
        ai = [i for i in range(nA_s) if bits[i] == 1]
        bi = [i - nA_s for i in range(nA_s, nA_s + nB_s) if bits[i] == 1]
        ok = len(ai) == 1 and len(bi) == 1
        a = A_sel[ai[0]] if ok else None
        b = B_sel[bi[0]] if ok else None
        hw.append(dict(sample=k, H_recomputed=H, H_archived=float(energy.H[k]),
                       n_plus=int((s > 0).sum()), nA1=len(ai), nB1=len(bi),
                       aux=int(s[-1]), legal=bool(ok), A=a, B=b,
                       V=float(V_sel[ai[0], bi[0]]) if ok else None,
                       hit_raw_opt=bool(ok and (a, b) in raw_pairs),
                       hit_sub_quant_opt=bool(ok and (a, b) in qset_sub)))
    legal_hw = [r for r in hw if r["legal"]]
    best_hw = min(legal_hw, key=lambda r: r["V"]) if legal_hw else None

    return dict(
        x=x,
        task_id=task["task_id"], platform_task_id=task.get("platform_task_id"),
        device=task.get("device"), hardware_ms=task.get("hardware_ms"),
        runtime_s=task.get("runtime_s"),
        topk=cfg["topk"], mfactor=cfg["mfactor"], samples=cfg["samples"],
        n_qubo=cfg["n_qubo"], n_ising=cfg["n_ising"], aux_bits=cfg["aux_bits"],
        M=cfg["M"], resol_raw=cfg["resol_raw"], resol_adj=cfg["resol_adj"],
        input_shape=list(V_in.shape),
        input_matrix_sha256=matrix_sha256(A_in, B_in, V_in),
        archived_input_sha256=cfg["input_matrix_sha256"],
        submitted_sha256=numeric_matrix_sha256(adj_sub),
        archived_submitted_sha256=cfg["submitted_matrix_sha256"],
        raw_ising_sha256=numeric_matrix_sha256(Is_),
        archived_raw_ising_sha256=cfg.get("raw_ising_matrix_sha256"),
        raw_ising_matches=bool(np.array_equal(Is_, I_raw_arch)),
        adj_matches_archived=bool(np.array_equal(adj_sub, adj_arch)),
        sub_A_equals_selection=bool(subm["A"] == A_sel),
        sub_B_equals_selection=bool(subm["B"] == B_sel),
        sub_V_equals_selection=bool(np.allclose(V_sub, V_sel, atol=1e-12, rtol=0)),
        raw_min=vmin, raw_argmin_count=len(raw_set), raw_argmin_top=sorted(raw_set),
        topk_retains_all_raw_argmins=bool(raw_pairs <= {(a, b) for a in A_sel for b in B_sel}),
        topk_sub_min=raw_sub_min, topk_sub_argmin_count=len(raw_sub_pairs),
        topk_sub_argmin_top=sorted(raw_sub_pairs),
        quantized_full_legal_min_h=hf_min,
        quantized_full_legal_set=qset_full_v,
        quantized_full_set_equals_raw=bool(qset_full == raw_pairs),
        quantized_full_retention=len(qset_full & raw_pairs) / max(len(raw_pairs), 1),
        quantized_full_extra=len(qset_full - raw_pairs),
        quantized_full_spearman=rho_full,
        quantized_topk_legal_min_h=hs_min,
        quantized_topk_legal_set=qset_sub_v,
        quantized_topk_set_equals_raw=bool(qset_sub == raw_sub_pairs),
        quantized_topk_retention=len(qset_sub & raw_sub_pairs) / max(len(raw_sub_pairs), 1),
        quantized_topk_extra=len(qset_sub - raw_sub_pairs),
        quantized_topk_spearman=rho_sub,
        submitted_space_exact=space,
        hw_returned=int(sol.shape[0]), hw_legal_count=len(legal_hw),
        hw_best=best_hw, hw_hits_raw_opt=int(sum(r["hit_raw_opt"] for r in hw)),
        hw_rows=hw,
    )


def main():
    # 正式基线 B：results/reproduction_20261127/predictions（不是 code/predictions 的基线 A）
    pred_b = ROOT / "results" / "reproduction_20261127" / "predictions"
    phys = pd.read_csv(pred_b / "pool_q3_phys.csv")
    base_a = pd.read_csv(PRED / "pool_q3_phys.csv")
    official = pd.read_csv(ROOT / "date" / "08_castelli_q3_pool.csv")
    keys_phys = set(map(tuple, phys[["A", "B", "X"]].astype(str).values))
    keys_a = set(map(tuple, base_a[["A", "B", "X"]].astype(str).values))
    keys_off = set(map(tuple, official[["A", "B", "X"]].astype(str).values))
    m = phys.merge(base_a, on=["A", "B", "X"], suffixes=("_B", "_A"))
    diff = np.abs(m.V_hat_B.to_numpy(float) - m.V_hat_A.to_numpy(float))
    vmatch = bool(np.all(diff <= 1e-12))

    gmin = float(phys.V_hat.min())
    g = phys[phys.V_hat <= gmin + 1e-12]
    per_x_min = {str(k): float(v) for k, v in phys.groupby("X").V_hat.min().items()}
    per_x_argmins = {}
    for x in per_x_min:
        sub = phys[(phys.X.astype(str) == x) & (phys.V_hat <= per_x_min[x] + 1e-12)]
        per_x_argmins[x] = sorted(map(tuple, sub[["A", "B"]].astype(str).values.tolist()))

    q2 = pd.read_csv(pred_b / "pool_q2_phys.csv")
    q2_map = dict(zip(map(tuple, q2[["A", "B"]].astype(str).values), q2.V_hat.to_numpy(float)))
    no2 = phys[phys.X.astype(str) == "NO2"]
    no2_map = dict(zip(map(tuple, no2[["A", "B"]].astype(str).values), no2.V_hat.to_numpy(float)))
    same_keys = set(q2_map) == set(no2_map)
    vmax_diff = max(abs(no2_map[k] - q2_map[k]) for k in q2_map) if same_keys else None

    out = dict(
        predictions=dict(
            baseline="B (results/reproduction_20261127/predictions)",
            baseline_B_shape=list(phys.shape), baseline_A_shape=list(base_a.shape),
            official_shape=list(official.shape),
            keys_B_equals_official=bool(keys_phys == keys_off),
            keys_A_equals_official=bool(keys_a == keys_off),
            baseline_B_equals_A=vmatch,
            n_v_hat_diff_B_vs_A=int((diff > 1e-12).sum()),
            max_abs_v_hat_diff_B_vs_A=float(diff.max()),
        ),
        q3_global=dict(
            raw_min=gmin, argmin_count=int(len(g)),
            argmin_by_x={str(k): int(v) for k, v in g.groupby("X").size().items()},
            argmin_list=sorted(map(tuple, g[["A", "B", "X"]].values.tolist())),
            per_x_min=per_x_min,
            per_x_argmin_count={x: len(v) for x, v in per_x_argmins.items()},
            per_x_argmins=per_x_argmins,
        ),
        q3_no2_equals_q2=dict(same_keys=bool(same_keys), max_abs_v_diff=vmax_diff,
                              q2_rows=int(len(q2)), no2_rows=int(len(no2))),
        per_x={},
    )
    for x in ("O3", "NO2", "FO2"):
        if x in ARCHIVE:
            out["per_x"][x] = q3_report(x)
        else:
            sub = phys[phys.X.astype(str) == x]
            Vdf = sub.pivot_table(index="A", columns="B", values="V_hat", aggfunc="first")
            A = [str(v) for v in Vdf.index]
            B = [str(v) for v in Vdf.columns]
            V = Vdf.to_numpy(float)
            out["per_x"][x] = dict(
                x=x, note="无独立 Q3 任务；与 Q2 使用同一 V̂ 矩阵（同一数值，序列化顺序不同）",
                input_shape=list(V.shape), input_matrix_sha256=matrix_sha256(A, B, V),
                raw_min=float(V.min()), raw_argmin_count=int((V <= V.min() + 1e-12).sum()),
                raw_argmin_top=[(A[i], B[j], float(V[i, j]))
                                for i, j in np.argwhere(V <= V.min() + 1e-12)])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_x"}, ensure_ascii=False, indent=2))
    for x, r in out["per_x"].items():
        print(f"\n=== {x} ===")
        for k in ("task_id", "platform_task_id", "device", "hardware_ms", "topk", "n_ising",
                  "input_matrix_sha256", "archived_input_sha256", "submitted_sha256",
                  "archived_submitted_sha256", "raw_ising_matches", "adj_matches_archived",
                  "sub_A_equals_selection", "sub_B_equals_selection", "sub_V_equals_selection",
                  "raw_min", "raw_argmin_count", "raw_argmin_top", "topk_retains_all_raw_argmins",
                  "quantized_full_legal_min_h", "quantized_full_legal_set",
                  "quantized_full_retention", "quantized_full_extra", "quantized_full_spearman",
                  "quantized_topk_legal_min_h", "quantized_topk_legal_set",
                  "quantized_topk_retention", "quantized_topk_extra", "quantized_topk_spearman",
                  "submitted_space_exact",
                  "hw_returned", "hw_legal_count", "hw_best", "hw_hits_raw_opt"):
            print(f"{k:34s}: {r.get(k)}")


if __name__ == "__main__":
    main()
