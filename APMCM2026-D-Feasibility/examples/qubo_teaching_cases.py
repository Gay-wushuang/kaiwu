"""Phase 2：QUBO / Ising 基础能力验证（仅通用教学问题，与 D 题无关）

每个案例都走同一条链路：
    数学问题 -> QUBO 表达式 -> QUBO 矩阵 -> Ising 矩阵 -> 求解器 -> 结果解码 -> 正确性检查

求解器统一使用 kw.classical.BruteForceOptimizer（实测无需 license），
另外用 numpy 全枚举独立计算 QUBO 目标值作为"已知正确结果"的对照。

运行：
    python examples/qubo_teaching_cases.py
退出码 0 表示所有案例 PASS。
"""

import json
import time
from pathlib import Path

import numpy as np

import kaiwu as kw

RESULTS_DIR = Path(__file__).resolve().parents[1] / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

RECORDS = []


def qubo_value_from_matrix(qmat, offset, x):
    """按上三角约定计算 x^T Q x + offset（x 为 0/1 向量）。"""
    return float(np.einsum("i,ij,j->", x, qmat, x) + offset)


def exhaustive_search(qmat, offset):
    """numpy 全枚举，返回 (最优目标值, 最优二进制解列表)。"""
    n = qmat.shape[0]
    best_val = np.inf
    best_solutions = []
    for code in range(2**n):
        x = np.array([(code >> i) & 1 for i in range(n)], dtype=float)
        val = qubo_value_from_matrix(qmat, offset, x)
        if val < best_val - 1e-9:
            best_val = val
            best_solutions = [x.astype(int).tolist()]
        elif abs(val - best_val) <= 1e-9:
            best_solutions.append(x.astype(int).tolist())
    return best_val, best_solutions


def solve_pipeline(model, case_name, check=None):
    """对给定 QuboModel 执行完整链路并记录结果。

    check(sol_dict, objective) -> bool，用变量名读取解，避免依赖变量排列顺序。
    """
    t0 = time.perf_counter()
    qmat = np.asarray(model.get_matrix())
    offset = float(model.make().offset)
    ising_model = kw.core.qubo_model_to_ising_model(model)
    imat = np.asarray(ising_model.get_matrix())
    t_build = time.perf_counter() - t0

    ising_vars = ising_model.get_variables()
    qubo_vars = model.get_variables()

    t1 = time.perf_counter()
    solver = kw.classical.BruteForceOptimizer()
    solutions = solver.solve(imat)
    t_solve = time.perf_counter() - t1

    best_qubo = np.inf
    best_sol_dict = None
    best_violations = None
    for sol in solutions:
        sol_dict = kw.get_sol_dict(sol, ising_vars)
        obj_val = kw.get_val(model.objective, sol_dict)
        unsatisfied, _ = model.verify_constraint(sol_dict)
        if obj_val < best_qubo - 1e-9:
            best_qubo = obj_val
            best_sol_dict = sol_dict
            best_violations = unsatisfied

    gt_val, gt_solutions = exhaustive_search(qmat, offset)

    ground_truth_ok = np.isclose(best_qubo, gt_val, atol=1e-6)
    constraint_ok = best_violations == 0
    known_ok = True if check is None else bool(check(best_sol_dict, best_qubo))
    passed = bool(ground_truth_ok and constraint_ok and known_ok)

    best_binary = {
        name: int(round(float(best_sol_dict[name]))) for name in qubo_vars.keys()
    }

    record = {
        "case": case_name,
        "n_qubo_vars": int(len(qubo_vars)),
        "qubo_matrix_shape": list(qmat.shape),
        "ising_matrix_shape": list(imat.shape),
        "qubo_offset": round(offset, 6),
        "build_time_s": round(t_build, 4),
        "solve_time_s": round(t_solve, 4),
        "solutions_returned": int(np.asarray(solutions).shape[0]),
        "best_objective": round(float(best_qubo), 6),
        "exhaustive_objective": round(float(gt_val), 6),
        "best_binary": best_binary,
        "hard_constraint_violations": best_violations,
        "objective_matches_exhaustive": bool(ground_truth_ok),
        "known_answer_matches": bool(known_ok),
        "exhaustive_solution_count": len(gt_solutions),
        "status": "PASS" if passed else "FAIL",
    }
    RECORDS.append(record)

    print(f"\n--- {case_name} ---")
    print(f"QUBO 变量数: {record['n_qubo_vars']}, QUBO 矩阵: {qmat.shape}, Ising 矩阵: {imat.shape}")
    print(f"建模+转换耗时: {record['build_time_s']} s, 暴力求解耗时: {record['solve_time_s']} s")
    print(f"最优目标值(SDK): {record['best_objective']}, 全枚举(+offset): {record['exhaustive_objective']}")
    print(f"最优解: {best_binary}, 硬约束违反数: {best_violations}")
    print(f"结论: {record['status']}")
    return record


def case_partition():
    """案例 1：整数划分。把 [8,7,6,5,4] 分成两组，使两组和之差最小。

    x_i=1 表示第 i 个数放入 A 组。
    差值 D = 2*sum(a_i x_i) - S，目标 H = D^2。
    """
    a = np.array([8, 7, 6, 5, 4])
    total = int(a.sum())
    x = [kw.core.Binary(f"p{i}") for i in range(len(a))]
    diff = 2 * kw.core.quicksum([a[i] * x[i] for i in range(len(a))]) - total
    model = kw.core.QuboModel()
    model.set_objective(diff * diff)

    def check(sol, _obj):
        a_side = int(sum(a[i] * sol[f"p{i}"] for i in range(len(a))))
        return abs(2 * a_side - total) == 0

    return solve_pipeline(model, "整数划分 [8,7,6,5,4]（最优差=0）", check=check)


def case_knapsack():
    """案例 2：0/1 背包。容量 10，物品重量 [3,4,5,2]，价值 [4,5,6,3]，最大化总价值。"""
    weights = np.array([3, 4, 5, 2])
    values = np.array([4, 5, 6, 3])
    capacity = 10
    x = [kw.core.Binary(f"k{i}") for i in range(len(weights))]

    model = kw.core.QuboModel()
    model.set_objective(-kw.core.quicksum([values[i] * x[i] for i in range(len(weights))]))
    model.add_constraint(
        kw.core.quicksum([weights[i] * x[i] for i in range(len(weights))]) <= capacity,
        "weight_cap",
        penalty=10,
    )

    def check(sol, obj):
        weight = int(sum(weights[i] * sol[f"k{i}"] for i in range(len(weights))))
        # 全枚举最优：选物品 0、2、3，重量 3+5+2=10，价值 4+6+3=13
        return weight <= capacity and np.isclose(obj, -13.0)

    return solve_pipeline(model, "0/1 背包（容量10，最优价值=13）", check=check)


def case_tsp():
    """案例 3：4 城市 TSP（官方教程同构问题）。x[u,j]=1 表示第 j 个位置访问城市 u。"""
    w = np.array(
        [
            [0, 4, 3, 2],
            [4, 0, 5, 1],
            [3, 5, 0, 6],
            [2, 1, 6, 0],
        ]
    )
    n = w.shape[0]
    x = kw.core.ndarray((n, n), "t", kw.core.Binary)

    def is_edge_used(u, v):
        return kw.core.quicksum([x[u, j] * x[v, j + 1] for j in range(-1, n - 1)])

    model = kw.core.QuboModel()
    edges = [(u, v) for u in range(n) for v in range(n) if w[u, v] != 0]
    model.set_objective(kw.core.quicksum([w[u, v] * is_edge_used(u, v) for u, v in edges]))
    model.add_constraint(x.sum(axis=0) == 1, "pos_cons", penalty=20)
    model.add_constraint(x.sum(axis=1) == 1, "node_cons", penalty=20)

    def check(sol, obj):
        mat = np.array([[int(round(sol[f"t[{u}][{j}]"])) for j in range(n)] for u in range(n)])
        # 全枚举最优回路 0->2->1->3->0，费用 3+5+1+2=11
        return (
            np.all(mat.sum(axis=0) == 1)
            and np.all(mat.sum(axis=1) == 1)
            and np.isclose(obj, 11.0)
        )

    return solve_pipeline(model, "4 城市 TSP（约束：每行每列恰一个 1）", check=check)


def case_independent_set():
    """案例 4：最大独立集（含硬约束的二进制优化）。

    图：0-1, 1-2, 2-3, 3-4, 4-0, 0-2 相邻。x_i=1 表示选中节点。
    最大化 sum x_i，约束每条边两端不能同时为 1。
    """
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0), (0, 2)]
    x = [kw.core.Binary(f"s{i}") for i in range(5)]

    model = kw.core.QuboModel()
    model.set_objective(-kw.core.quicksum(x))
    for idx, (u, v) in enumerate(edges):
        model.add_constraint(x[u] + x[v] <= 1, f"edge_{idx}", penalty=5)

    def check(sol, obj):
        chosen = [int(round(sol[f"s{i}"])) for i in range(5)]
        for u, v in edges:
            if chosen[u] == 1 and chosen[v] == 1:
                return False
        return np.isclose(obj, -2.0)  # 5 节点 5 环 + 弦，最大独立集为 2

    return solve_pipeline(model, "最大独立集（5 节点，硬约束：相邻不同时选中）", check=check)


def main():
    print("=" * 70)
    print("Phase 2：QUBO / Ising 教学案例链路验证")
    print("=" * 70)

    case_partition()
    case_knapsack()
    case_tsp()
    case_independent_set()

    out = RESULTS_DIR / "phase2_qubo_cases.json"
    out.write_text(json.dumps(RECORDS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {out}")

    failed = [r["case"] for r in RECORDS if r["status"] != "PASS"]
    print("\n=== 汇总 ===")
    for r in RECORDS:
        print(f"{r['status']:4s} | {r['case']} | vars={r['n_qubo_vars']} | obj={r['best_objective']}")
    if failed:
        print(f"\n存在 FAIL 案例: {failed}")
        raise SystemExit(1)
    print("\n全部案例 PASS")


if __name__ == "__main__":
    main()
