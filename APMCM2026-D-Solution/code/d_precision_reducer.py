# -*- coding: utf-8 -*-
"""PrecisionReducer 离线旁路验证：直接取整、动态范围压缩与变量拆分对照。

只使用本地 CPU 和 Kaiwu 预处理接口，不调用 license、不联网、不提交 CIM、不写结果文件。
数学模型完全复用 ``d_submit_cim``；本脚本不修改正式实验的直接取整默认链路。

教学例子：
    python code/d_precision_reducer.py --demo
只读冻结输入（默认 top-K=13，避免无意构造过大的拆分矩阵）：
    python code/d_precision_reducer.py --input-version B-Q2-NO2 --topk 13

指标均限定在合法 one-hot 子空间。候选求解器只用于验证 SDK 的矩阵变换和解恢复，
不是优化器，不能据此声明采样质量或物理全局最优。
"""
from __future__ import annotations

import argparse
import itertools
import json
import time

import numpy as np

import d_submit_cim as S
import precision_reducer as PRR
import kaiwu as kw
import kaiwu.preprocess as pp

PRECISION = 8
TEACHING_A = ["a1", "a2", "a3"]
TEACHING_B = ["b1", "b2", "b3"]
TEACHING_V = np.array([
    [0.2544058321170608, 1.478493748067384, 0.3913056598906419],
    [0.12384047029690515, 1.1967842146480763, 1.7915155034825632],
    [0.053886822769405596, 1.6102719797833385, 0.38034003345668155],
])


def _json_number(value):
    """把 SDK 返回的 numpy 标量转成严格 JSON；无穷位宽用字符串保留。"""
    value = float(value)
    return value if np.isfinite(value) else str(value)


def _validate_matrix(matrix):
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"Ising 矩阵必须为方阵，实际为 {matrix.shape}")
    if not np.isfinite(matrix).all() or not np.array_equal(matrix, matrix.T):
        raise ValueError("SDK 返回了非有限或非对称 Ising 矩阵")
    return matrix


def bit_width_info(matrix, precision=PRECISION):
    info = pp.calculate_ising_matrix_bit_width(matrix, precision)
    return {key: _json_number(value) for key, value in info.items()}


def build_ising(V, mfactor=1.0):
    """复用正式模型的 QUBO/Ising 构造；不在这里调整罚项公式。"""
    V = np.asarray(V, dtype=float)
    if V.ndim != 2 or min(V.shape) < 2 or not np.isfinite(V).all():
        raise ValueError("V 必须是至少 2×2 的有限数值矩阵")
    if not np.isfinite(mfactor):
        raise ValueError("mfactor 必须是有限数值")
    Q, offset, M0 = S.build_qubo(V)
    M = M0 * mfactor
    if mfactor != 1.0:
        Q, offset, M = S.build_qubo(V, M=M)
    I, bias = S.to_ising(Q)
    return {"Q": Q, "I": _validate_matrix(I), "offset": offset, "bias": bias,
            "M": M, "M0": M0}


def direct_adapt(I):
    return _validate_matrix(pp.adjust_ising_matrix_precision(I, PRECISION))


def reducer_adapt(I, truncated_precision=20, precision=PRECISION):
    """用公开预处理 API 重放 Reducer 文档所述变换，保留完整审计信息。"""
    if truncated_precision < precision:
        raise ValueError("truncated_precision 不能小于目标 precision")
    started = time.perf_counter()
    truncated = _validate_matrix(pp.adjust_ising_matrix_precision(I, truncated_precision))
    split, representatives = pp.perform_precision_adaption_split(
        truncated, param_bit=precision)
    split = _validate_matrix(split)
    representatives = np.asarray(representatives, dtype=int)
    before_fallback = bit_width_info(split, precision)
    fallback = before_fallback["precision"] == "inf" or before_fallback["precision"] > precision
    matrix = _validate_matrix(pp.adjust_ising_matrix_precision(split, precision)) \
        if fallback else split
    return {
        "matrix": matrix,
        "split_matrix": split,
        "truncated_matrix": truncated,
        "representatives": representatives,
        "fallback_direct_rounding": bool(fallback),
        "bit_width_before_fallback": before_fallback,
        "bit_width": bit_width_info(matrix, precision),
        "adaptation_ms": (time.perf_counter() - started) * 1000,
        "precision": precision,
        "target_bits": None,
        "truncated_precision": truncated_precision,
    }


class CandidateSolver(kw.core.IsingSolver):
    """把已知原始状态构造成拆分状态，专门验证 Reducer 的恢复契约。"""

    def __init__(self, candidates, representatives):
        super().__init__()
        self.candidates = np.asarray(candidates, dtype=np.int8)
        self.representatives = np.asarray(representatives, dtype=int)
        self.received_matrix = None

    def _solve(self, ising_matrix=None):
        self.received_matrix = np.asarray(ising_matrix).copy()
        return np.asarray([
            pp.construct_split_solution(state, self.representatives)
            for state in self.candidates
        ], dtype=np.int8)


def verify_reducer_recovery(I, candidates, transform, nA=None, nB=None):
    """让 Reducer 包装无 license 的候选求解器，并核对其真实下发矩阵。"""
    solver = CandidateSolver(candidates, transform["representatives"])
    reducer = pp.PrecisionReducer(
        solver, precision=transform["precision"], target_bits=None,
        only_feasible_solution=False,
        truncated_precision=transform["truncated_precision"])
    started = time.perf_counter()
    restored = np.asarray(reducer.solve(I))
    elapsed_ms = (time.perf_counter() - started) * 1000
    expected = np.asarray(candidates, dtype=np.int8)
    expected = expected * expected[:, [-1]]  # SDK negtail_flip：末端辅助自旋规范化为 +1
    if not np.array_equal(solver.received_matrix, transform["matrix"]):
        raise RuntimeError("Reducer 实际下发矩阵与公开 truncate+split 重放结果不一致")
    if restored.shape != expected.shape or not np.isin(restored, [-1, 1]).all():
        raise RuntimeError(f"Reducer 恢复解形状或取值异常：{restored.shape}")
    result = {
        "roundtrip_exact": bool(np.array_equal(restored, expected)),
        "candidate_count": int(restored.shape[0]),
        "returned_shape": list(restored.shape),
        "actual_split_shape": list(solver.received_matrix.shape),
        "aux_gauge_values": [int(v) for v in np.unique(restored[:, -1])],
        "solve_and_restore_ms": elapsed_ms,
    }
    if nA is not None and nB is not None:
        bits = PRR.logical_bits_from_spins(restored)
        legal = ((bits[:, :nA].sum(axis=1) == 1) &
                 (bits[:, nA:nA + nB].sum(axis=1) == 1))
        result["legal_candidate_count"] = int(legal.sum())
        result["legal_candidate_rate"] = float(legal.mean())
    return result


def legal_states(nA, nB):
    """按 V.ravel() 顺序返回全部合法 one-hot 状态，原模型辅助自旋固定为 +1。"""
    states = []
    for i in range(nA):
        for j in range(nB):
            bits = np.zeros(nA + nB, dtype=np.int8)
            bits[i] = 1
            bits[nA + j] = 1
            states.append(np.concatenate([2 * bits.astype(float) - 1, [1.0]]))
    return np.asarray(states)


def _energies(matrix, states):
    states = np.asarray(states, dtype=float)
    return -np.einsum("ni,ij,nj->n", states, matrix, states)


def _best_summary(energies, A, B):
    index = int(np.argmin(energies))
    nB = len(B)
    ordered = np.sort(energies)
    return {
        "best_pair": [A[index // nB], B[index % nB]],
        "best_energy": float(energies[index]),
        "best_v": None,
        "energy_gap_to_second": float(ordered[1] - ordered[0]),
        "minimum_tie_count": int(np.isclose(energies, ordered[0], rtol=0, atol=1e-9).sum()),
    }


def fidelity_metrics(raw_I, adapted_I, raw_states, adapted_states, A, B, V, topk=8):
    """比较同一合法指派集合；top-k 与排序均不混入非法或拆分不一致状态。"""
    raw_e = _energies(raw_I, raw_states)
    adapted_e = _energies(adapted_I, adapted_states)
    n = len(raw_e)
    k = min(int(topk), n)
    raw_top = set(np.argsort(raw_e, kind="stable")[:k].tolist())
    adapted_top = set(np.argsort(adapted_e, kind="stable")[:k].tolist())
    raw_best = set(np.flatnonzero(np.isclose(raw_e, raw_e.min(), rtol=0, atol=1e-12)).tolist())
    adapted_best = set(np.flatnonzero(np.isclose(adapted_e, adapted_e.min(), rtol=0, atol=1e-9)).tolist())

    left, right = np.triu_indices(n, 1)
    raw_delta = raw_e[right] - raw_e[left]
    adapted_delta = adapted_e[right] - adapted_e[left]
    comparable = ~np.isclose(raw_delta, 0, rtol=0, atol=1e-12)
    adapted_ties = np.isclose(adapted_delta, 0, rtol=0, atol=1e-9) & comparable
    agreed = np.sign(raw_delta[comparable]) == np.sign(adapted_delta[comparable])

    result = _best_summary(adapted_e, A, B)
    best_index = int(np.argmin(adapted_e))
    result.update({
        "best_v": float(np.asarray(V).ravel()[best_index]),
        "raw_optimum_retained": bool(raw_best & adapted_best),
        "topk": k,
        "topk_retained": len(raw_top & adapted_top),
        "topk_retention": len(raw_top & adapted_top) / k,
        "pairwise_comparable_pairs": int(comparable.sum()),
        "pairwise_agreement": float(agreed.mean()) if agreed.size else None,
        "new_ties_among_comparable_pairs": int(adapted_ties.sum()),
        "raw": _best_summary(raw_e, A, B),
    })
    result["raw"]["best_v"] = float(np.min(V))
    return result


def _adapted_states(states, representatives=None):
    if representatives is None:
        return states
    return np.asarray([pp.construct_split_solution(s, representatives) for s in states])


def _candidate_states(raw_states, n, seed):
    if n <= 8:
        return np.asarray(list(itertools.product([-1, 1], repeat=n)), dtype=np.int8)
    rng = np.random.default_rng(seed)
    random_states = rng.choice([-1, 1], size=(16, n)).astype(np.int8)
    return np.concatenate([raw_states.astype(np.int8), random_states], axis=0)


def run_comparison(A, B, V, mfactor=1.0, topk_metric=8, truncated_precision=20,
                   mutate_iterations=100, seed=20261128):
    """运行离线确定性对照；耗时单独报告，不设未经基准验证的性能阈值。"""
    A, B = list(A), list(B)
    V = np.asarray(V, dtype=float)
    model = build_ising(V, mfactor)
    I = model["I"]
    raw_states = legal_states(len(A), len(B))
    if len(raw_states) != V.size:
        raise ValueError("A/B 标签数量与 V 形状不一致")

    started = time.perf_counter()
    direct = direct_adapt(I)
    direct_ms = (time.perf_counter() - started) * 1000
    reducer = reducer_adapt(I, truncated_precision=truncated_precision)
    reducer_states = _adapted_states(raw_states, reducer["representatives"])
    candidates = _candidate_states(raw_states, I.shape[0], seed)
    recovery = verify_reducer_recovery(I, candidates, reducer, len(A), len(B))

    strategies = {"direct": fidelity_metrics(
        I, direct, raw_states, raw_states, A, B, V, topk_metric)}
    strategies["direct"]["adaptation_ms"] = direct_ms
    strategies["precision_reducer"] = fidelity_metrics(
        I, reducer["matrix"], raw_states, reducer_states, A, B, V, topk_metric)
    strategies["precision_reducer"]["adaptation_ms"] = reducer["adaptation_ms"]

    mutation = {"enabled": bool(mutate_iterations), "iterations": int(mutate_iterations)}
    if mutate_iterations:
        started = time.perf_counter()
        mutated = _validate_matrix(pp.perform_precision_adaption_mutate(
            I, iterations=int(mutate_iterations)))
        mutated_direct = direct_adapt(mutated)
        mutation["adaptation_ms"] = (time.perf_counter() - started) * 1000
        mutation["dynamic_range_before"] = _json_number(pp.get_dynamic_range_metric(I))
        mutation["dynamic_range_after"] = _json_number(pp.get_dynamic_range_metric(mutated))
        strategies["mutate_then_direct"] = fidelity_metrics(
            I, mutated_direct, raw_states, raw_states, A, B, V, topk_metric)
        strategies["mutate_then_direct"]["adaptation_ms"] = mutation["adaptation_ms"]

    return {
        "scope": "offline legal-one-hot validation; no network, license, CIM submission or output files",
        "input": {
            "shape": list(V.shape), "n_qubo": int(model["Q"].shape[0]),
            "n_ising": int(I.shape[0]), "M": float(model["M"]),
            "M0": float(model["M0"]), "mfactor": float(mfactor),
        },
        "parameters": {"precision": PRECISION, "target_bits": None,
                       "truncated_precision": int(truncated_precision), "seed": int(seed)},
        "dynamic_range": {
            "raw": _json_number(pp.get_dynamic_range_metric(I)),
            "reducer_split": _json_number(pp.get_dynamic_range_metric(reducer["matrix"])),
        },
        "reducer": {
            "split_shape": list(reducer["matrix"].shape),
            "added_split_variables": int(reducer["matrix"].shape[0] - I.shape[0]),
            "original_aux_spin_indices": [int(I.shape[0] - 1)],
            "split_representative_indices": reducer["representatives"].tolist(),
            "fallback_direct_rounding": reducer["fallback_direct_rounding"],
            "bit_width_before_fallback": reducer["bit_width_before_fallback"],
            "bit_width": reducer["bit_width"],
            "recovery": recovery,
        },
        "mutation": mutation,
        "strategies": strategies,
        "notes": [
            "candidate solver verifies transformation/recovery only; it is not an optimizer or sampling-quality benchmark",
            "legal_candidate_rate describes probe coverage, not an optimizer's valid-solution rate",
            "energy gaps use each matrix's own scale; use retention and pairwise agreement for cross-matrix fidelity",
            "PrecisionReducer may still fall back to direct rounding after splitting; fallback_direct_rounding records that event",
            "target_bits=None imposes no hardware size cap; review added_split_variables before any migration",
            "mutate is exploratory and is not guaranteed to reduce dynamic range or preserve an 8-bit argmin",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true", help="运行内置非赛题 3×3 教学矩阵")
    source.add_argument("--input-version", help="只读加载 experiment_input 已登记版本")
    parser.add_argument("--topk", type=int, default=13, help="冻结输入的每轴预筛规模；0 为全量")
    parser.add_argument("--mfactor", type=float, default=1.0)
    parser.add_argument("--topk-metric", type=int, default=8, help="保真指标中的 top-k")
    parser.add_argument("--truncated-precision", type=int, default=20)
    parser.add_argument("--mutate-iterations", type=int, default=100,
                        help="动态范围压缩迭代数；0 表示跳过该探索对照")
    parser.add_argument("--seed", type=int, default=20261128)
    args = parser.parse_args(argv)
    if args.topk < 0 or args.topk_metric < 1 or args.mutate_iterations < 0:
        parser.error("topk/mutate-iterations 不能为负，topk-metric 必须为正")

    if args.demo:
        A, B, V = TEACHING_A, TEACHING_B, TEACHING_V
        source_info = {"kind": "teaching", "version": None}
    else:
        import d_experiment as dx
        import experiment_input as exin
        loaded = exin.load(args.input_version)
        if args.topk and args.topk > len(loaded.A):
            parser.error(f"topk={args.topk} 超过可用标签数 {len(loaded.A)}")
        A, B, V = dx.select_topk(loaded.A, loaded.B, loaded.V, args.topk)
        source_info = {"kind": loaded.kind, "version": loaded.version,
                       "registered_shape": list(loaded.shape), "selected_topk": args.topk,
                       "matrix_sha256": loaded.matrix_sha256}

    result = run_comparison(A, B, V, mfactor=args.mfactor, topk_metric=args.topk_metric,
                            truncated_precision=args.truncated_precision,
                            mutate_iterations=args.mutate_iterations, seed=args.seed)
    result["input"].update(source_info)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
