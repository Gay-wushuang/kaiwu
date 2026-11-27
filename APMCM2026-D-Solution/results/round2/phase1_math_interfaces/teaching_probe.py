# -*- coding: utf-8 -*-
"""T002 第一阶段证据脚本：教学例子 + 第一轮结果的机械复核。

只读现有归档；不提交真机、不修改第一轮数据、不训练模型。
运行：
    %LOCALAPPDATA%\\kaiwu-verify\\Scripts\\python.exe results/round2/phase1_math_interfaces/teaching_probe.py
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code"))
import kaiwu as kw                     # noqa: E402
import kaiwu.preprocess as pp          # noqa: E402
import d_submit_cim as S               # noqa: E402

OUT = Path(__file__).resolve().parent
TASKS = [
    ("B_Q2_baseline", "t20261128-003014-b_q2_baseline-be06017f"),
    ("B_Q2_m3x", "t20261128-003124-b_q2_m3x-e2530a24"),
    ("B_Q2_k8", "t20261128-003140-b_q2_k8-7be3225f"),
    ("B_Q3_O3_baseline", "t20261128-003159-b_q3_o3_baseline-7cd9ce6b"),
    ("B_Q3_FO2_baseline", "t20261128-003216-b_q3_fo2_baseline-ca295ce6"),
]

# 独立教学矩阵（非赛题元素，3×3 指派）
V = np.array([
    [0.2544058321170608, 1.478493748067384, 0.3913056598906419],
    [0.12384047029690515, 1.1967842146480763, 1.7915155034825632],
    [0.053886822769405596, 1.6102719797833385, 0.38034003345668155],
])
nA, nB = V.shape
M0 = float(max(2 * (V.max() - V.min()), 1.0) + 15)


def sel_sum(bits):
    return sum(V[i, j] for i in range(nA) for j in range(nB)
               if bits[i] == 1 and bits[nA + j] == 1)


def counts(bits):
    return int(sum(bits[:nA])), int(sum(bits[nA:nA + nB]))


def spin(bits):
    return np.concatenate([2 * np.asarray(bits, float) - 1, [1.0]])


def legal_pairs():
    return [(i, j) for i in range(nA) for j in range(nB)]


def teaching_case(mfactor):
    M = M0 * mfactor
    Q, offset, _ = S.build_qubo(V, M=M)
    I, bias = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    Qa, offa = kw.core.ising_matrix_to_qubo_matrix(adj)
    r_raw = S.resolution(I, nA, nB)
    r_adj = S.resolution(adj, nA, nB)
    pen_err = ising_err = 0.0
    legal_q, illegal_q = [], []
    adj_rows = []
    for bits in itertools.product([0, 1], repeat=nA + nB):
        x = np.asarray(bits, float)
        s = spin(bits)
        qv = float(x @ Q @ x) + offset
        kA, kB = counts(bits)
        pen = M * ((kA - 1) ** 2 + (kB - 1) ** 2)
        pen_err = max(pen_err, abs(qv - sel_sum(bits) - pen))
        ising_err = max(ising_err, abs(float(-s @ I @ s) + bias - float(x @ Q @ x)))
        if kA == 1 and kB == 1:
            legal_q.append(qv)
            adj_rows.append({"bits": list(bits),
                             "H_adj": float(-s @ adj @ s),
                             "V_eff": float(x @ Qa @ x) + offa})
        else:
            illegal_q.append(qv)
    raw_candidates = [float(V[i, j]) for i, j in legal_pairs()]
    raw_min = min(raw_candidates)
    raw_set = [[i, j] for i, j in legal_pairs() if abs(V[i, j] - raw_min) < 1e-12]
    adj_min = min(r["H_adj"] for r in adj_rows)
    adj_set = [r["bits"] for r in adj_rows if abs(r["H_adj"] - adj_min) < 1e-9]
    ranked = sorted(adj_rows, key=lambda r: r["H_adj"])
    rank = {tuple(r["bits"]): k + 1 for k, r in enumerate(ranked)}
    raw_bits = [tuple([1 if i == a else 0 for i in range(nA)] +
                      [1 if j == b else 0 for j in range(nB)]) for a, b in raw_set]
    adj_bits_set = {tuple(r["bits"]) for r in adj_rows if abs(r["H_adj"] - adj_min) < 1e-9}
    raw_in_adj = bool({tuple(b) for b in raw_bits} & adj_bits_set)
    return {
        "mfactor": mfactor, "M": M, "M0": M0,
        "min_V": float(V.min()), "max_V": float(V.max()),
        "M_gt_minV": bool(M > V.min()), "M_gt_maxV": bool(M > V.max()),
        "resolution_raw": r_raw["resol"], "resolution_adj": r_adj["resol"],
        "raw_top": r_raw["top"], "raw_obj": r_raw["obj"], "raw_step": r_raw["step"],
        "adj_top": r_adj["top"], "adj_obj": r_adj["obj"], "adj_step": r_adj["step"],
        "adj_max_abs": float(np.abs(adj).max()),
        "bit_width_check": {k: (float(v) if k == "multiplier" else v)
                            for k, v in pp.calculate_ising_matrix_bit_width(adj, 8).items()},
        "best_legal_qubo": min(legal_q), "best_illegal_qubo": min(illegal_q),
        "illegal_minus_legal": min(illegal_q) - min(legal_q),
        "penalty_formula_max_error": pen_err,
        "qubo_ising_identity_max_error": ising_err,
        "H_adj_vs_Veff_max_error": max(abs(r["H_adj"] - r["V_eff"]) for r in adj_rows),
        "raw_argmin": raw_set, "raw_argmin_adj_ranks": [rank[b] for b in raw_bits],
        "raw_in_adjusted_argmin": raw_in_adj,
        "adjusted_argmin_bits": adj_set,
        "adjusted_tie_count": len(adj_set),
    }


def round1_case(name, tid):
    d = ROOT / "experiments" / "tasks" / tid
    cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
    mp = json.loads((d / "input" / "submitted_mapping.json").read_text(encoding="utf-8"))
    Vt = pd.read_csv(d / "input" / "submitted_target_V.csv", index_col=0).values
    adj = np.loadtxt(d / "input" / "ising_matrix.csv", delimiter=",", ndmin=2)
    raw_I = np.loadtxt(d / "input" / "ising_matrix_raw.csv", delimiter=",", ndmin=2)
    sol = np.load(d / "raw" / "solutions.npz")["solutions"]
    A, B = mp["A"], mp["B"]
    nA2, nB2 = len(A), len(B)

    def legal_s(bits):
        return np.concatenate([2 * np.asarray(bits, float) - 1, [1.0]])

    raw_pairs = [(i, j) for i in range(nA2) for j in range(nB2)]
    raw_min = min(float(Vt[i, j]) for i, j in raw_pairs)
    raw_set = [(i, j) for i, j in raw_pairs if abs(float(Vt[i, j]) - raw_min) < 1e-12]
    adj_rows = []
    for i, j in raw_pairs:
        bits = [1 if k == i else 0 for k in range(nA2)] + \
               [1 if k == j else 0 for k in range(nB2)]
        adj_rows.append({"pair": [i, j], "H": float(-legal_s(bits) @ adj @ legal_s(bits))})
    adj_min = min(r["H"] for r in adj_rows)
    adj_set = [r["pair"] for r in adj_rows if abs(r["H"] - adj_min) < 1e-9]
    ranked = sorted(adj_rows, key=lambda r: r["H"])
    rank = {tuple(r["pair"]): k + 1 for k, r in enumerate(ranked)}

    returned_samples = []
    legal_returned = []
    for k, s in enumerate(np.atleast_2d(sol)):
        bits = ((s + 1) // 2).astype(int)
        ia = np.flatnonzero(bits[:nA2])
        ib = np.flatnonzero(bits[nA2:nA2 + nB2])
        h = float(-s @ adj @ s)
        legal = bool(len(ia) == 1 and len(ib) == 1 and bits[-1] == 1)
        item = {"sample": int(k), "bits": bits.tolist(), "H": h, "legal": legal}
        if legal:
            item.update({"pair": [A[ia[0]], B[ib[0]]],
                         "V": float(Vt[ia[0], ib[0]])})
            legal_returned.append({"pair": [int(ia[0]), int(ib[0])],
                                   "H": h, "V": float(Vt[ia[0], ib[0]])})
        returned_samples.append(item)
    returned = len(returned_samples)
    best_legal = min(legal_returned, key=lambda x: x["H"]) if legal_returned else None
    quant_hit = bool(best_legal and abs(best_legal["H"] - adj_min) < 1e-9)
    raw_hit = bool(best_legal and tuple(best_legal["pair"]) in {tuple(p) for p in raw_set})
    return {
        "task_name": name, "task_id": tid, "status": json.loads((d / "task.json").read_text(encoding="utf-8"))["status"],
        "M": cfg["M"], "M0": cfg["M0"], "mfactor": cfg["mfactor"], "topk": cfg["topk"],
        "n_ising": cfg["n_ising"],
        "config_resol_raw": cfg["resol_raw"], "config_resol_adj": cfg["resol_adj"],
        "recomputed_resol_raw": S.resolution(raw_I, nA2, nB2)["resol"],
        "recomputed_resol_adj": S.resolution(adj, nA2, nB2)["resol"],
        "raw_maxJ": S.resolution(raw_I, nA2, nB2)["top"],
        "raw_obj": S.resolution(raw_I, nA2, nB2)["obj"],
        "adj_maxJ": S.resolution(adj, nA2, nB2)["top"],
        "adj_obj": S.resolution(adj, nA2, nB2)["obj"],
        "raw_argmin": [[A[i], B[j]] for i, j in raw_set],
        "raw_argmin_ranks": [rank[p] for p in raw_set],
        "raw_optima_in_adjusted_argmin": bool({tuple(p) for p in raw_set} &
                                              {tuple(p) for p in adj_set}),
        "adjusted_argmin": [[A[i], B[j]] for i, j in adj_set],
        "returned": returned, "legal_returned": len(legal_returned),
        "returned_samples": returned_samples,
        "best_returned_legal": ({"pair": [A[best_legal["pair"][0]], B[best_legal["pair"][1]]],
                                 "H": best_legal["H"], "V": best_legal["V"]}
                                if best_legal else None),
        "quantized_legal_optimum_hit": quant_hit,
        "raw_objective_optimum_hit": raw_hit,
    }


def main():
    teaching = [teaching_case(mf) for mf in [0.001, 0.005, 1.0, 3.0, 10.0]]
    round1 = [round1_case(n, t) for n, t in TASKS]
    total_returned = sum(r["returned"] for r in round1)
    total_legal = sum(r["legal_returned"] for r in round1)
    quant_hits = sum(r["quantized_legal_optimum_hit"] for r in round1)
    raw_hits = sum(r["raw_objective_optimum_hit"] for r in round1)
    raw_preserved = sum(r["raw_optima_in_adjusted_argmin"] for r in round1)

    q2 = pd.read_csv(ROOT / "results" / "reproduction_20261127" / "predictions" / "pool_q2_phys.csv")
    q3 = pd.read_csv(ROOT / "results" / "reproduction_20261127" / "predictions" / "pool_q3_phys.csv")
    zero_counts = {
        "Q2_NO2": int(((q2.X == "NO2") & (q2.V_hat == 0)).sum()),
        "Q3_total": int((q3.V_hat == 0).sum()),
        "Q3_by_X": {str(k): int(v) for k, v in q3[q3.V_hat == 0].groupby("X").size().items()},
    }

    payload = {
        "schema_version": 1,
        "scope": "T002 phase 1: finite-precision fidelity and constraint validity",
        "teaching_matrix": V.tolist(),
        "default_M0": M0,
        "notes": [
            "rank 字段只用于展示；判断原始最优是否保留应使用集合交集，不能用 rank == 1 代替。",
            "returned_samples 中所有样本含 bits/legal/H；仅合法样本含 pair/V；非法样本的 pair/V 缺失不表示 0。",
            "resolution 的步长取 max|I|/127，分子分母来自同一 Ising 矩阵；它衡量目标系数占多少量化格，不能单独决定合法解排序。",
            "QUBO/Ising 恒等式按 aux=+1 约定；若返回 aux=-1，应先整体翻转全部自旋到 aux=+1 再解码。",
            "本轮只使用 adjust_ising_matrix_precision 直接适配（对称缩放后就近取整），未使用动态范围压缩或变量拆分。",
        ],
        "teaching_cases": teaching,
        "round1_tasks": round1,
        "round1_aggregate": {
            "tasks": len(round1), "returned": total_returned, "legal": total_legal,
            "quantized_legal_optimum_hits": quant_hits,
            "raw_objective_optimum_hits": raw_hits,
            "raw_argmin_preserved_in_adjusted": raw_preserved,
            "metric_definitions": {
                "quantized_legal_optimum_hit": "该任务至少一个返回合法解属于 adjusted_argmin 集合",
                "raw_objective_optimum_hit": "该任务至少一个返回合法解属于 raw_argmin 集合",
                "raw_argmin_preserved_in_adjusted": "该任务的 raw_argmin 集合与 adjusted_argmin 集合有交集",
            },
        },
        "prediction_zero_counts": zero_counts,
        "math_tests": {"file": "tests/test_math_interfaces.py", "result": "5/5 PASS"},
        "sdk_docs": [
            {"url": "https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/precision.html",
             "facts": ["SPQC uses 8-bit integer Ising coefficients [-128,127]",
                       "adjust_ising_matrix_precision is symmetric linear scaling + nearest rounding",
                       "extreme values cause small coefficients to collapse; docs recommend dynamic-range compression or variable splitting for complex cases",
                       "dynamic-range compression can preserve optimum only under explicit scaling conditions"]},
            {"url": "https://kaiwu-sdk-docs.qboson.com/zh/latest/source/modules/kaiwu.preprocess.html",
             "facts": ["adjust_ising_matrix_precision may cause large precision loss when one element dominates",
                       "calculate_ising_matrix_bit_width reports precision and multiplier",
                       "perform_precision_adaption_mutate / split are separate mechanisms not used by this workflow"]},
        ],
    }
    (OUT / "teaching_example.json").write_text(
        json.dumps({"teaching_matrix": V.tolist(), "default_M0": M0,
                    "notes": payload["notes"][:3], "cases": teaching},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "round1_recheck.json").write_text(
        json.dumps({"tasks": round1, "aggregate": payload["round1_aggregate"],
                    "prediction_zero_counts": zero_counts,
                    "sample_fields": "all samples: sample,bits,legal,H; legal samples add pair,V; missing pair/V for illegal is not zero",
                    "metric_definitions": payload["round1_aggregate"]["metric_definitions"],
                    "notes": payload["notes"]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"aggregate": payload["round1_aggregate"],
                      "zero_counts": zero_counts,
                      "teaching": [{"mfactor": t["mfactor"],
                                    "resol_raw": round(t["resolution_raw"], 3),
                                    "resol_adj": round(t["resolution_adj"], 3),
                                    "illegal_minus_legal": round(t["illegal_minus_legal"], 6),
                                    "raw_in_adjusted": t["raw_in_adjusted_argmin"],
                                    "adj_ties": t["adjusted_tie_count"]} for t in teaching]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
