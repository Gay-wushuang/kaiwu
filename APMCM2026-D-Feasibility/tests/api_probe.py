"""Kaiwu SDK API 探针：在不消耗 license 的前提下确认建模与转换 API 的真实签名。

仅用于环境核查，不属于任何竞赛求解方案。
"""

import inspect

import numpy as np

import kaiwu as kw


def show(name, obj):
    try:
        sig = inspect.signature(obj)
    except Exception as exc:  # 编译扩展可能不暴露签名
        sig = f"<unavailable: {exc}>"
    print(f"{name}: {sig}")
    doc = (obj.__doc__ or "").strip().splitlines()
    if doc:
        print(f"    doc: {doc[0]}")


print("=== 版本 ===")
import importlib.metadata as md

print("kaiwu dist:", md.version("kaiwu"))
print("kaiwu-community dist:", md.version("kaiwu-community"))
print("kw.__version__:", getattr(kw, "__version__", None))

print("\n=== 核心 API 签名 ===")
show("kw.core.ndarray", kw.core.ndarray)
show("kw.core.QuboModel", kw.core.QuboModel)
show("kw.core.QuboModel.set_objective", kw.core.QuboModel.set_objective)
show("kw.core.QuboModel.add_constraint", kw.core.QuboModel.add_constraint)
show("kw.core.QuboModel.verify_constraint", kw.core.QuboModel.verify_constraint)
show("kw.core.QuboModel.get_matrix", kw.core.QuboModel.get_matrix)
show("kw.core.quicksum", kw.core.quicksum)
show("kw.core.get_sol_dict", kw.core.get_sol_dict)
show("kw.core.get_val", kw.core.get_val)
show("kw.core.qubo_model_to_ising_model", kw.core.qubo_model_to_ising_model)
show("kw.core.ising_matrix_to_qubo_matrix", kw.core.ising_matrix_to_qubo_matrix)
show("kw.core.qubo_matrix_to_qubo_model", kw.core.qubo_matrix_to_qubo_model)
show("kw.classical.BruteForceOptimizer", kw.classical.BruteForceOptimizer)
show("kw.preprocess.adjust_ising_matrix_precision", kw.preprocess.adjust_ising_matrix_precision)

print("\n=== 建模 + QUBO→Ising 转换（不调用求解器）===")
x = kw.core.ndarray(3, "x", kw.core.Binary)
model = kw.core.QuboModel()
model.set_objective(2 * x[0] + 3 * x[1] + x[2] + 4 * x[0] * x[1])
print("objective:", model.objective)
qmat = model.get_matrix()
print("QUBO matrix:\n", np.asarray(qmat))
print("offset:", model.get_offset())

ising_model = kw.core.qubo_model_to_ising_model(model)
imat = ising_model.get_matrix()
print("Ising matrix:\n", np.asarray(imat))
print("IsingModel public attrs:", [a for a in dir(ising_model) if not a.startswith("_")])
print("ising h vector:", getattr(ising_model, "h", "no h attr"))
print("ising offset:", getattr(ising_model, "offset", "no offset attr"))

back, _ = kw.core.ising_matrix_to_qubo_matrix(np.asarray(imat))
print("Ising back to QUBO:\n", np.asarray(back))

print("\n=== 暴力求解器端到端（无 license）===")
bf = kw.classical.BruteForceOptimizer()
sol = bf.solve(np.asarray(imat))
print("solutions shape:", sol.shape)
print("first solution:", sol[0])
print("best energy (hamiltonian):", kw.common.hamiltonian(np.asarray(imat), sol))
ising_vars = ising_model.get_variables()
print("ising_model.get_variables():", ising_vars)
print("model.get_variables():", model.get_variables())
sol_dict = kw.get_sol_dict(sol[0], ising_vars)
print("sol_dict:", sol_dict, "qubo objective value:", kw.get_val(model.objective, sol_dict))
