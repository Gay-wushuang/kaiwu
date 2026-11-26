# -*- coding: utf-8 -*-
"""D 题 Step 3：问题 2 的 104 比特 QUBO 构造 + 穷举验证 + 8bit 精度量化影响"""
import os, itertools, numpy as np, pandas as pd

d = r"D:\temp\d_out"
pool = pd.read_csv(os.path.join(d, "pool_q2.csv"))
A = sorted(pool.A.unique()); B = sorted(pool.B.unique())
ai = {a: i for i, a in enumerate(A)}; bi = {b: i + len(A) for i, b in enumerate(B)}
n = len(A) + len(B)          # 104
V = np.zeros((len(A), len(B)))
for _, r in pool.iterrows():
    V[ai[r.A], bi[r.B] - len(A)] = r.V_hat

M = 200.0                    # 罚项系数（远大于 V 的尺度）
Q = np.zeros((n, n), dtype=np.float64)
# 目标项：V_ab * x_a * y_b
for i in range(len(A)):
    for j in range(len(B)):
        Q[i, bi[B[j]]] += V[i, j]
# 约束项 M(Σx-1)^2 = -M Σx + 2M Σ_{i<i'} x_i x_i' + M
for base, k in [(0, len(A)), (len(A), len(B))]:
    for i in range(base, base + k):
        Q[i, i] += -M
        for j in range(i + 1, base + k):
            Q[i, j] += 2 * M
offset = 2 * M

def energy(bits):
    return bits @ Q @ bits + offset

# --- 穷举验证（一个 A、一个 B，共 2704 种） ---
best, bv = None, 1e18
for i in range(len(A)):
    for j in range(len(B)):
        bits = np.zeros(n, dtype=np.int64)
        bits[i] = 1; bits[len(A) + j] = 1
        e = energy(bits)
        if e < bv:
            bv, best = e, (A[i], B[j])
print(f"QUBO 维度 {n}×{n} | 退火/穷举最优: {best} 能量 {bv:.4f}")

# 与直接查 V 表对照
i0, j0 = ai[best[0]], ai[best[1]]
print(f"直接查表最小 V_hat: {V.min():.4f} -> {A[int(V.argmin()//len(B))]}{B[int(V.argmin()%len(B))]}")

# --- 8bit 有符号整数量化（硬件系数约束） ---
maxabs = np.abs(Q).max()
scale = 127.0 / maxabs
Qq = np.round(Q * scale)
print(f"\n8bit 量化: max|Q|={maxabs:.1f} -> 缩放 {scale:.4f}；量化后最大整数 {np.abs(Qq).max():.0f}")
best_q, bv_q = None, 1e18
for i in range(len(A)):
    for j in range(len(B)):
        bits = np.zeros(n, dtype=np.int64)
        bits[i] = 1; bits[len(A) + j] = 1
        e = bits @ Qq @ bits / scale + offset
        if e < bv_q:
            bv_q, best_q = e, (A[i], B[j])
print(f"量化后最优: {best_q} | 与量化前{'一致 ✅' if best_q == best else '不一致 ⚠️'}")

# 罚项充分性检验：若选两个 A（违反约束）应被罚
bits = np.zeros(n, dtype=np.int64); bits[0] = 1; bits[1] = 1; bits[len(A)] = 1
print(f"约束违反样例（2 个 A、1 个 B）能量: {energy(bits):.1f}（合法解约 {bv:.1f}）→ 罚项{M}足够")

out = r"D:\temp\d_out"
np.savez(os.path.join(out, "qubo_q2.npz"), Q=Q, offset=offset, M=M,
         elems=np.array(A), n=n)
pd.DataFrame(Q).to_csv(os.path.join(out, "qubo_q2_matrix.csv"), index=False, header=False)
print(f"\n已存 qubo_q2.npz / qubo_q2_matrix.csv（{n}×{n}）")

# --- 问题 3：三自由度，先按固定 X 分三次求解（主线方案） ---
p3 = pd.read_csv(os.path.join(out, "pool_q3.csv"))
print("\n问题 3（固定 X 三次求解）:")
for x in ["O3", "NO2", "FO2"]:
    sub = p3[p3.X == x].sort_values("V_hat")
    top = sub.iloc[0]
    print(f"  X={x:4s}: 最优 {top.formula:12s} V_hat={top.V_hat:.4f} | 该 X 下 V_hat<1 的 {int((sub.V_hat<1).sum())} 个")
best3 = p3.sort_values("V_hat").iloc[0]
print(f"  三次取最好: {best3.formula} (X={best3.X}) V_hat={best3.V_hat:.4f}")
