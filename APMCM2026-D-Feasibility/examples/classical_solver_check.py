"""Phase 3：本地经典求解器与精度适配工具实测

测试对象（以实测为准，不预设文档说法）：
1. kw.classical.BruteForceOptimizer      —— 是否可离线运行
2. kw.classical.SimulatedAnnealingOptimizer —— 是否需要 license
3. kw.classical.TabuSearchOptimizer      —— 是否需要 license
4. kw.sampler.SimulatedAnnealingSampler  —— 是否需要 license
5. kw.preprocess 精度适配工具链           —— 8bit 约束下的可用性

求解器可用性在子进程中探测（stdin=DEVNULL），避免 license 交互式输入卡死主流程。

运行：python examples/classical_solver_check.py
"""

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parents[1] / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_CODE = r"""
import json, numpy as np, kaiwu as kw

matrix = -np.array([
    [0., 1., 0., 1., 1.],
    [1., 0., 0., 1., 1.],
    [0., 0., 0., 1., 1.],
    [1., 1., 1., 0., 1.],
    [1., 1., 1., 1., 0.],
])

result = {}
try:
    sol = kw.classical.BruteForceOptimizer().solve(matrix)
    result["BruteForceOptimizer"] = {"status": "PASS", "n_solutions": int(np.asarray(sol).shape[0])}
except Exception as e:
    result["BruteForceOptimizer"] = {"status": "FAIL", "error": f"{type(e).__name__}: {e}"}

try:
    opt = kw.classical.SimulatedAnnealingOptimizer(initial_temperature=100, alpha=0.99,
                                                   cutoff_temperature=0.001, iterations_per_t=10,
                                                   size_limit=10)
    sol = opt.solve(matrix)
    result["SimulatedAnnealingOptimizer"] = {"status": "PASS", "n_solutions": int(np.asarray(sol).shape[0])}
except EOFError as e:
    result["SimulatedAnnealingOptimizer"] = {"status": "BLOCKED_LICENSE", "error": "license 输入被中断（EOF）"}
except ValueError as e:
    result["SimulatedAnnealingOptimizer"] = {"status": "BLOCKED_LICENSE", "error": str(e)}
except Exception as e:
    result["SimulatedAnnealingOptimizer"] = {"status": "FAIL", "error": f"{type(e).__name__}: {e}"}

try:
    opt = kw.classical.TabuSearchOptimizer(100, size_limit=1)
    sol = opt.solve(matrix)
    result["TabuSearchOptimizer"] = {"status": "PASS", "n_solutions": int(np.asarray(sol).shape[0])}
except EOFError:
    result["TabuSearchOptimizer"] = {"status": "BLOCKED_LICENSE", "error": "license 输入被中断（EOF）"}
except ValueError as e:
    result["TabuSearchOptimizer"] = {"status": "BLOCKED_LICENSE", "error": str(e)}
except Exception as e:
    result["TabuSearchOptimizer"] = {"status": "FAIL", "error": f"{type(e).__name__}: {e}"}

try:
    sampler = kw.sampler.SimulatedAnnealingSampler(alpha=0.99, cutoff_temperature=0.001, iterations_per_t=10)
    out = sampler.solve(matrix)
    result["SimulatedAnnealingSampler"] = {"status": "PASS", "type": type(out).__name__}
except EOFError:
    result["SimulatedAnnealingSampler"] = {"status": "BLOCKED_LICENSE", "error": "license 输入被中断（EOF）"}
except ValueError as e:
    result["SimulatedAnnealingSampler"] = {"status": "BLOCKED_LICENSE", "error": str(e)}
except Exception as e:
    result["SimulatedAnnealingSampler"] = {"status": "FAIL", "error": f"{type(e).__name__}: {e}"}

print("RESULT_JSON:" + json.dumps(result, ensure_ascii=False))
"""


def qubo_value_from_matrix(qmat, offset, x):
    return float(np.einsum("i,ij,j->", x, qmat, x) + offset)


def all_spins(n):
    """生成全部 2^n 自旋配置（±1），用于独立核对最优能量。"""
    codes = np.arange(2**n, dtype=np.int64)
    bits = ((codes[:, None] >> np.arange(n)[None, :]) & 1).astype(np.int8)
    return (bits * 2 - 1).astype(np.int8)


def best_energy_bruteforce(ising_mat):
    """独立枚举，返回 SDK 约定下的最小 Ising 能量。

    SDK 约定（由 kw.common.hamiltonian 实测确认）：H(s) = -s^T J s，
    求解器的目标是使 H 最小，即最大化 s^T J s。
    """
    spins = all_spins(ising_mat.shape[0])
    energies = -np.einsum("ij,ij->i", spins @ ising_mat, spins)
    return float(energies.min()), spins[int(np.argmin(energies))]


def probe_solvers():
    """子进程探测求解器可用性与 license 依赖。"""
    proc = subprocess.run(
        [sys.executable, "-c", PROBE_CODE],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=300,
    )
    record = {
        "stdout": proc.stdout.strip()[-2000:],
        "stderr_tail": proc.stderr.strip()[-800:],
        "returncode": proc.returncode,
    }
    try:
        payload = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT_JSON:")][-1]
        record["solvers"] = json.loads(payload[len("RESULT_JSON:"):])
    except Exception:
        record["solvers"] = {"parse_error": "无法解析探测输出"}
    return record


def bench_bruteforce_scale():
    """BruteForce 规模-耗时曲线（随机对称 Ising 矩阵，固定随机种子）。"""
    import kaiwu as kw

    rng = np.random.default_rng(20261126)
    rows = []
    for n in [8, 12, 16, 18, 20]:
        mat = rng.integers(-10, 11, size=(n, n)).astype(float)
        mat = np.triu(mat, 1)
        mat = mat + mat.T
        t0 = time.perf_counter()
        sol = np.asarray(kw.classical.BruteForceOptimizer().solve(mat))
        elapsed = time.perf_counter() - t0

        sdk_best = float(np.min(-np.einsum("ij,ij->i", sol @ mat, sol)))
        gt_best, _ = best_energy_bruteforce(mat)
        rows.append(
            {
                "n_bits": n,
                "ising_shape": list(mat.shape),
                "solutions_returned": int(sol.shape[0]),
                "solve_time_s": round(elapsed, 4),
                "sdk_best_energy": sdk_best,
                "independent_best_energy": gt_best,
                "energy_match": bool(abs(sdk_best - gt_best) < 1e-9),
            }
        )
        print(f"n={n:2d} time={elapsed:8.4f}s sdk={sdk_best:10.2f} gt={gt_best:10.2f} match={rows[-1]['energy_match']}")
    return rows


def precision_pipeline():
    """8bit 精度适配工具链实测：bit width / 截断 / 动态范围压缩 / 变量拆分。"""
    import kaiwu as kw

    # 用 4 城市 TSP 的 QUBO 作为被测模型（教学案例，非赛题）
    w = np.array([[0, 4, 3, 2], [4, 0, 5, 1], [3, 5, 0, 6], [2, 1, 6, 0]])
    n = w.shape[0]
    x = kw.core.ndarray((n, n), "t", kw.core.Binary)

    def is_edge_used(u, v):
        return kw.core.quicksum([x[u, j] * x[v, j + 1] for j in range(-1, n - 1)])

    model = kw.core.QuboModel()
    edges = [(u, v) for u in range(n) for v in range(n) if w[u, v] != 0]
    model.set_objective(kw.core.quicksum([w[u, v] * is_edge_used(u, v) for u, v in edges]))
    model.add_constraint(x.sum(axis=0) == 1, "pos_cons", penalty=20)
    model.add_constraint(x.sum(axis=1) == 1, "node_cons", penalty=20)

    ising_mat = np.asarray(kw.core.qubo_model_to_ising_model(model).get_matrix())
    bw = kw.preprocess.calculate_ising_matrix_bit_width(ising_mat, 8)

    # 原始矩阵的精确最优能量（BruteForce，17 bit 可枚举）
    t0 = time.perf_counter()
    sol_orig = np.asarray(kw.classical.BruteForceOptimizer().solve(ising_mat))
    t_orig = time.perf_counter() - t0
    orig_opt = float(np.min(-np.einsum("ij,ij->i", sol_orig @ ising_mat, sol_orig)))

    out = {
        "ising_shape": list(ising_mat.shape),
        "ising_abs_min_nonzero": float(np.min(np.abs(ising_mat[np.abs(ising_mat) > 0]))),
        "ising_abs_max": float(np.max(np.abs(ising_mat))),
        "dynamic_range_metric": float(kw.preprocess.get_dynamic_range_metric(ising_mat)),
        "bit_width_8": {k: (None if np.isinf(v) else float(v)) for k, v in bw.items()},
        "bit_width_8_exact_representable": bool(bw["precision"] <= 8),
        "original_optimum_energy": orig_opt,
        "original_solve_time_s": round(t_orig, 4),
    }

    def eval_solution(sol):
        return float(-sol @ ising_mat @ sol)

    # 方法一：直接截断
    t0 = time.perf_counter()
    trunc = np.asarray(kw.preprocess.adjust_ising_matrix_precision(ising_mat, bit_width=8))
    t_trunc = time.perf_counter() - t0
    sol_trunc = np.asarray(kw.classical.BruteForceOptimizer().solve(trunc))
    trunc_energy = eval_solution(sol_trunc[0])
    out["truncate"] = {
        "shape": list(trunc.shape),
        "time_s": round(t_trunc, 4),
        "max_abs_after": float(np.max(np.abs(trunc))),
        "all_integer": bool(np.allclose(trunc, np.round(trunc))),
        "energy_of_best_truncated_solution_on_original": trunc_energy,
        "optimum_preserved": bool(abs(trunc_energy - orig_opt) < 1e-6),
    }

    # 方法二：动态范围压缩（目标是保持最优解不变）
    t0 = time.perf_counter()
    mutated = np.asarray(kw.preprocess.perform_precision_adaption_mutate(ising_mat))
    t_mut = time.perf_counter() - t0
    sol_mut = np.asarray(kw.classical.BruteForceOptimizer().solve(mutated))
    mut_energy = eval_solution(sol_mut[0])
    out["mutate"] = {
        "shape": list(mutated.shape),
        "time_s": round(t_mut, 4),
        "max_abs_after": float(np.max(np.abs(mutated))),
        "bit_width_after": {
            k: (None if np.isinf(v) else float(v))
            for k, v in kw.preprocess.calculate_ising_matrix_bit_width(mutated, 8).items()
        },
        "energy_of_best_mutated_solution_on_original": mut_energy,
        "optimum_preserved": bool(abs(mut_energy - orig_opt) < 1e-6),
    }

    # 方法三：变量拆分
    t0 = time.perf_counter()
    split_mat, split_idx = kw.preprocess.perform_precision_adaption_split(
        ising_mat, param_bit=8, min_increment=0.125
    )
    split_mat = np.asarray(split_mat)
    t_split = time.perf_counter() - t0
    out["split"] = {
        "shape": list(split_mat.shape),
        "time_s": round(t_split, 4),
        "bit_width_after": {
            k: (None if np.isinf(v) else float(v))
            for k, v in kw.preprocess.calculate_ising_matrix_bit_width(split_mat, 8).items()
        },
        "expansion_bits": int(split_mat.shape[0] - ising_mat.shape[0]),
    }

    # 拆分矩阵用 BruteForce 求解并还原，检查最优解是否保持（拆分后位数需可控）
    if split_mat.shape[0] <= 22:
        sol_split = np.asarray(kw.classical.BruteForceOptimizer().solve(split_mat))
        restored = np.asarray(kw.preprocess.restore_split_solution(sol_split[0], split_idx))
        restored_energy = eval_solution(restored)
        out["split"]["restored_shape"] = list(restored.shape)
        out["split"]["energy_of_restored_solution_on_original"] = restored_energy
        out["split"]["optimum_preserved"] = bool(abs(restored_energy - orig_opt) < 1e-6)
    else:
        out["split"]["optimum_preserved"] = "SKIPPED_TOO_LARGE"

    return out


def bench_stochastic_solvers():
    """无 license 可用的随机求解器：TabuSearch 与 SimulatedAnnealingSampler 稳定性。"""
    import kaiwu as kw

    kw.common.set_log_level("WARNING")
    rng = np.random.default_rng(2026)
    n = 12
    mat = rng.integers(-10, 11, size=(n, n)).astype(float)
    mat = np.triu(mat, 1)
    mat = mat + mat.T
    gt_best, _ = best_energy_bruteforce(mat)

    def energies_of(solutions):
        arr = np.atleast_2d(np.asarray(solutions))
        return -np.einsum("ij,ij->i", arr @ mat, arr)

    out = {"matrix_shape": list(mat.shape), "ground_truth_best_energy": gt_best, "runs": 5}

    # 禁忌搜索
    tabu_energies, tabu_times = [], []
    for _ in range(out["runs"]):
        t0 = time.perf_counter()
        sol = kw.classical.TabuSearchOptimizer(1000, size_limit=1).solve(mat)
        tabu_times.append(time.perf_counter() - t0)
        tabu_energies.append(float(np.min(energies_of(sol))))
    out["tabu"] = {
        "energies": tabu_energies,
        "times_s": [round(t, 4) for t in tabu_times],
        "hit_rate": float(np.mean([abs(e - gt_best) < 1e-9 for e in tabu_energies])),
        "mean_gap": float(np.mean([e - gt_best for e in tabu_energies])),
    }

    # 模拟退火采样器（输出多条链的结果）
    sa_energies, sa_times = [], []
    for _ in range(3):
        t0 = time.perf_counter()
        sampler = kw.sampler.SimulatedAnnealingSampler(
            alpha=0.99, cutoff_temperature=0.001, iterations_per_t=10
        )
        sol = sampler.solve(mat)
        sa_times.append(time.perf_counter() - t0)
        sa_energies.append(float(np.min(energies_of(sol))))
    out["sa_sampler"] = {
        "energies": sa_energies,
        "times_s": [round(t, 4) for t in sa_times],
        "hit_rate": float(np.mean([abs(e - gt_best) < 1e-9 for e in sa_energies])),
        "mean_gap": float(np.mean([e - gt_best for e in sa_energies])),
        "runs": 3,
    }
    return out


def main():
    print("=" * 78)
    print("Phase 3：本地经典求解器与精度工具实测")
    print("=" * 78)
    print(f"Python {platform.python_version()} | {platform.platform()}")

    print("\n[1] 求解器可用性探测（子进程，stdin=DEVNULL）")
    solvers = probe_solvers()
    for name, info in solvers["solvers"].items():
        print(f"  {name}: {info['status']}  {info.get('error', '')}")

    print("\n[2] BruteForce 规模-耗时")
    scale = bench_bruteforce_scale()

    print("\n[3] 8bit 精度适配工具链")
    prec = precision_pipeline()
    print(f"  Ising 矩阵 {prec['ising_shape']}, 动态范围指标={prec['dynamic_range_metric']:.3f}")
    print(f"  8bit 可精确表示: {prec['bit_width_8_exact_representable']} ({prec['bit_width_8']})")
    print(f"  原始最优能量={prec['original_optimum_energy']}")
    print(f"  截断: 保最优={prec['truncate']['optimum_preserved']}")
    print(f"  压缩: 保最优={prec['mutate']['optimum_preserved']}")
    print(f"  拆分: {prec['ising_shape']} -> {prec['split']['shape']}, 保最优={prec['split']['optimum_preserved']}")

    print("\n[4] 无 license 随机求解器稳定性（12 bit 随机 Ising）")
    stoch = bench_stochastic_solvers()
    print(f"  真实最优能量: {stoch['ground_truth_best_energy']}")
    print(f"  TabuSearch: 命中率={stoch['tabu']['hit_rate']:.2f}, 平均间隙={stoch['tabu']['mean_gap']:.2f}")
    print(f"  SA Sampler: 命中率={stoch['sa_sampler']['hit_rate']:.2f}, 平均间隙={stoch['sa_sampler']['mean_gap']:.2f}")

    out = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "solver_probe": solvers,
        "bruteforce_scale": scale,
        "precision": prec,
        "stochastic_solvers": stoch,
    }
    path = RESULTS_DIR / "phase3_classical.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {path}")


if __name__ == "__main__":
    main()
