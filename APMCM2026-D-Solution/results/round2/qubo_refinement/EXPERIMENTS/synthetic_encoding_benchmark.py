# -*- coding: utf-8 -*-
"""T002-A V2：非赛题合成基准，比较 one-hot 与 domain-wall 在 8bit 量化下的
目标保真、约束有效性、变量/矩阵成本。全空间穷举，不使用赛题数据。"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))
import kaiwu as kw                     # noqa: E402
import kaiwu.preprocess as pp          # noqa: E402
import d_submit_cim as S               # noqa: E402

OUT = Path(__file__).resolve().parent
D = 4
N_INSTANCES = 200
RNG = np.random.default_rng(20261128)


def e_onehot(d, r):
    n = d
    const, lin = 0.0, np.zeros(n)
    lin[r] = 1.0
    return const, lin


def e_domain_wall(d, r):
    n = d - 1
    const, lin = 0.0, np.zeros(n)
    if r == 0:
        const, lin[0] = 1.0, -1.0
    elif r == d - 1:
        lin[d - 2] = 1.0
    else:
        lin[r - 1], lin[r] = 1.0, -1.0
    return const, lin


def add_lin(Q, offset, form, c):
    const, lin = form
    offset += c * const
    Q[np.diag_indices_from(Q)] += c * lin
    return offset


def add_prod(Q, offset, f, g, c):
    a0, a = f
    b0, b = g
    offset += c * a0 * b0
    diag = c * (a0 * b + b0 * a + a * b)
    Q[np.diag_indices_from(Q)] += diag
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            Q[i, j] += c * (a[i] * b[j] + a[j] * b[i])
    return offset


def build_domain_wall(V, M):
    d = V.shape[0]
    n = 2 * (d - 1)
    Q = np.zeros((n, n))
    offset = 0.0
    ea = [e_domain_wall(d, r) for r in range(d)]
    eb = [e_domain_wall(d, r) for r in range(d)]
    # 将本地 e 向量嵌入全局变量索引
    def embed(form, base):
        const, lin = form
        g = np.zeros(n)
        g[base:base + len(lin)] = lin
        return const, g
    ea_g = [embed(e, 0) for e in ea]
    eb_g = [embed(e, d - 1) for e in eb]
    # 成本由 V 提供；V 的一元/成对成本在这里全部按表加入
    for r in range(d):
        # 行/列的一元项由 V 的对应值承载；这里不另加向量
        pass
    for r in range(d):
        for q in range(d):
            offset = add_prod(Q, offset, ea_g[r], eb_g[q], float(V[r, q]))
    # domain-wall 合法性罚项：sum (1-t_i) t_{i+1}
    for base in (0, d - 1):
        for i in range(d - 2):
            left = np.zeros(n); left[base + i] = -1.0
            right = np.zeros(n); right[base + i + 1] = 1.0
            offset = add_prod(Q, offset, (1.0, left), (0.0, right), M)
    return Q, offset


def build_onehot(V, M):
    d = V.shape[0]
    n = 2 * d
    Q = np.zeros((n, n))
    offset = 0.0
    ea = [e_onehot(d, r) for r in range(d)]
    eb = [e_onehot(d, r) for r in range(d)]

    def embed(form, base):
        const, lin = form
        g = np.zeros(n)
        g[base:base + len(lin)] = lin
        return const, g

    ea_g = [embed(e, 0) for e in ea]
    eb_g = [embed(e, d) for e in eb]
    for r in range(d):
        for q in range(d):
            offset = add_prod(Q, offset, ea_g[r], eb_g[q], float(V[r, q]))
    for base in (0, d):
        s_const, s_lin = 0.0, np.zeros(n)
        forms = ea_g if base == 0 else eb_g
        for form in forms:
            s_const += form[0]
            s_lin += form[1]
        # (sum e - 1)^2
        offset = add_prod(Q, offset, (s_const - 1.0, s_lin), (s_const - 1.0, s_lin), M)
    return Q, offset


def code_map(d, encoding):
    if encoding == "onehot":
        return {tuple(1 if i == r else 0 for i in range(d)): r for r in range(d)}
    return {tuple(1 if r >= i else 0 for i in range(1, d)): r for r in range(d)}


def _rank(a):
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), float)
    ranks[order] = np.arange(len(a))
    for v in np.unique(a):
        m = a == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    return ranks


def spearman(a, b):
    rx, ry = _rank(np.asarray(a, float)), _rank(np.asarray(b, float))
    if np.std(rx) == 0 or np.std(ry) == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def eval_instance(V, M, encoding):
    d = V.shape[0]
    Q, offset = build_onehot(V, M) if encoding == "onehot" else build_domain_wall(V, M)
    n = Q.shape[0]
    I, bias = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    Qa, offa = kw.core.ising_matrix_to_qubo_matrix(adj)
    cmap = code_map(d, encoding)
    legal = {}
    exact = {}
    quant = {}
    exact_all = []
    quant_all = []
    for bits in itertools.product([0, 1], repeat=n):
        x = np.asarray(bits, float)
        e = float(x @ Q @ x) + offset
        q = float(x @ Qa @ x) + offa
        exact_all.append(e)
        quant_all.append(q)
        if encoding == "onehot":
            ia = [i for i in range(d) if bits[i] == 1]
            ib = [i for i in range(d) if bits[d + i] == 1]
            lab = (ia[0], ib[0]) if len(ia) == 1 and len(ib) == 1 else None
        else:
            lab = (cmap.get(tuple(bits[:d - 1])), cmap.get(tuple(bits[d - 1:])))
            if lab[0] is None or lab[1] is None:
                lab = None
        if lab is not None:
            legal[lab] = True
            exact[lab] = e
            quant[lab] = q
    exact_all = np.asarray(exact_all)
    quant_all = np.asarray(quant_all)
    legal_mask = np.array([False] * len(exact_all))
    # 重新计算 legal mask（更直接）
    idx = 0
    for bits in itertools.product([0, 1], repeat=n):
        if encoding == "onehot":
            ia = [i for i in range(d) if bits[i] == 1]
            ib = [i for i in range(d) if bits[d + i] == 1]
            ok = len(ia) == 1 and len(ib) == 1
        else:
            ok = tuple(bits[:d - 1]) in cmap and tuple(bits[d - 1:]) in cmap
        legal_mask[idx] = ok
        idx += 1
    Vf = V.flatten()
    labels = [(r, q) for r in range(d) for q in range(d)]
    quant_vec = np.array([quant[l] for l in labels])
    raw_min = Vf.min()
    raw_set = {labels[i] for i in range(len(labels)) if abs(Vf[i] - raw_min) < 1e-12}
    qmin = quant_vec.min()
    qset = {labels[i] for i in range(len(labels)) if abs(quant_vec[i] - qmin) < 1e-12}
    inter = raw_set & qset
    exact_legal = float(exact_all[legal_mask].min())
    exact_illegal = float(exact_all[~legal_mask].min())
    quant_legal = float(quant_all[legal_mask].min())
    quant_illegal = float(quant_all[~legal_mask].min())
    # Spearman
    rho = spearman(Vf, quant_vec)
    return {
        "encoding": encoding, "n_var": int(n), "n_ising": int(adj.shape[0]),
        "aux": int(adj.shape[0] - n),
        "legal_equal_V": bool(np.max(np.abs(np.array([exact[l] for l in labels]) - Vf)) < 1e-8),
        "raw_set": sorted(raw_set), "quant_set": sorted(qset),
        "intersection_size": len(inter), "retention": len(inter) / len(raw_set),
        "non_original": len(qset - raw_set),
        "spearman": rho,
        "exact_best_legal": exact_legal, "exact_best_illegal": exact_illegal,
        "exact_gap": exact_illegal - exact_legal,
        "quant_best_legal": quant_legal, "quant_best_illegal": quant_illegal,
        "quant_gap": quant_illegal - quant_legal,
        "exact_valid": bool(exact_legal < exact_illegal),
        "quant_valid": bool(quant_legal < quant_illegal),
    }


def main():
    t0 = time.perf_counter()
    aggregates = {}
    instances = []
    for k in range(N_INSTANCES):
        V = RNG.uniform(0.0, 5.0, size=(D, D))
        for regime, M in (("strong", 1.05 * V.max()), ("weak", 0.5 * V.min())):
            for enc in ("onehot", "domainwall"):
                r = eval_instance(V, M, enc)
                r.update({"instance": k, "regime": regime, "M": float(M),
                          "v_min": float(V.min()), "v_max": float(V.max())})
                instances.append(r)
                key = (enc, regime)
                aggregates.setdefault(key, []).append(r)
    summary = {}
    for key, rows in aggregates.items():
        rhos = [r["spearman"] for r in rows if r["spearman"] is not None]
        summary[f"{key[0]}|{key[1]}"] = {
            "n": len(rows),
            "mean_retention": float(np.mean([r["retention"] for r in rows])),
            "mean_non_original": float(np.mean([r["non_original"] for r in rows])),
            "mean_spearman": float(np.mean(rhos)) if rhos else None,
            "spearman_defined": len(rhos),
            "exact_valid_rate": float(np.mean([r["exact_valid"] for r in rows])),
            "quant_valid_rate": float(np.mean([r["quant_valid"] for r in rows])),
            "quant_zero_gap_count": int(sum(abs(r["quant_gap"]) <= 1e-12 for r in rows)),
            "quant_negative_gap_count": int(sum(r["quant_gap"] < -1e-12 for r in rows)),
            "mean_exact_gap": float(np.mean([r["exact_gap"] for r in rows])),
            "mean_quant_gap": float(np.mean([r["quant_gap"] for r in rows])),
            "legal_equal_V_all": all(r["legal_equal_V"] for r in rows),
            "n_var": rows[0]["n_var"], "n_ising": rows[0]["n_ising"],
            "aux": rows[0]["aux"],
        }
    # 编码间 quant set 是否不同（同实例/同 regime）
    diff = 0
    for k in range(N_INSTANCES):
        for regime in ("strong", "weak"):
            oh = next(r for r in instances if r["instance"] == k and r["regime"] == regime and r["encoding"] == "onehot")
            dw = next(r for r in instances if r["instance"] == k and r["regime"] == regime and r["encoding"] == "domainwall")
            if set(map(tuple, oh["quant_set"])) != set(map(tuple, dw["quant_set"])):
                diff += 1
    payload = {
        "schema_version": 1,
        "scope": "synthetic non-competition benchmark; not a formal round-2 experiment",
        "d": D, "instances": N_INSTANCES, "seed": 20261128,
        "summary": summary,
        "quant_set_diff_instances": diff,
        "constant_rank_spearman": spearman(np.arange(16), np.ones(16)),
        "runtime_s": time.perf_counter() - t0,
        "instances_detail": instances,
    }
    (OUT / "synthetic_benchmark_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": summary, "quant_set_diff_instances": diff,
                      "runtime_s": payload["runtime_s"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
