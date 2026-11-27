import itertools
import sys
from pathlib import Path

import numpy as np

CODE = Path(r"e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\code")
sys.path.insert(0, str(CODE))

import kaiwu.preprocess as pp
import d_submit_cim as S


def heading(t):
    print("\n" + "=" * 70)
    print(t)
    print("=" * 70)


def identity_check():
    heading("A. QUBO -> Ising 恒等式（3x3 非对称 V，32 个 QUBO 状态 x 2 个辅助自旋）")
    V = np.array([[0.0, 1.0, 5.0], [2.0, 0.0, 4.0], [3.0, 3.0, 0.0]])
    Q, offset, M = S.build_qubo(V)
    I, bias = S.to_ising(Q)
    n = Q.shape[0]
    print(f"Q {Q.shape} | I {I.shape} | M={M:.3f} | bias={bias:.6f}")
    print(f"I 对称: {np.allclose(I, I.T)} | I 对角 max|.|: {np.abs(np.diag(I)).max():.6e}")
    devs = {-1: [], 1: []}
    for xb in itertools.product([0, 1], repeat=n):
        x = np.array(xb, dtype=float)
        qv = float(x @ Q @ x)
        for aux in (-1, 1):
            s = np.concatenate([2 * x - 1, [aux]])
            H = float(-s @ I @ s)
            devs[aux].append(qv - H)
    for aux in (-1, 1):
        arr = np.array(devs[aux])
        print(f"aux={aux:+d}: QUBO-H  min={arr.min():.6f} max={arr.max():.6f} "
              f"| 与 bias 差 max={np.abs(arr - bias).max():.6f}")
    print(f"结论：QUBO = H + bias 仅对 aux=+1 成立？ "
          f"{np.abs(np.array(devs[1]) - bias).max() < 1e-9 and np.abs(np.array(devs[-1]) - bias).max() > 1e-9}")


def sa_check(adj, label):
    states = [np.array(s, dtype=float) for s in itertools.product([-1, 1], repeat=len(adj))]
    H = {tuple(s.astype(int)): float(-s @ adj @ s) for s in states}
    e2 = e4 = 0.0
    for s in states:
        for i in range(len(adj)):
            sn = s.copy(); sn[i] = -sn[i]
            exact = H[tuple(sn.astype(int))] - H[tuple(s.astype(int))]
            code2 = 2 * s[i] * (adj[i] @ s) - 2 * adj[i, i]
            code4 = 4 * s[i] * (adj[i] @ s) - 4 * adj[i, i]
            e2 = max(e2, abs(code2 - exact / 2))
            e4 = max(e4, abs(code4 - exact))
    print(f"{label}: 状态数 {len(states)} | max|2s(Js)-2Jii - ΔH/2| = {e2:.3e} "
          f"| max|4s(Js)-4Jii - ΔH| = {e4:.3e}")


def sa_all():
    heading("B. 模拟退火 ΔH 全状态枚举")
    rng = np.random.default_rng(20261127)
    for n in (4, 5):
        J = rng.normal(size=(n, n))
        J = (J + J.T) / 2
        sa_check(J, f"随机对称 J {n}x{n}（含非零对角）")
    V2 = np.array([[0.0, 3.0], [4.0, 0.0]])
    Q, offset, M = S.build_qubo(V2)
    I, bias = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    print(f"实际小块 2x2: QUBO {Q.shape[0]} -> Ising {adj.shape[0]} | M={M:.2f} | adj 对角 max {np.abs(np.diag(adj)).max():.0f}")
    sa_check(adj, "实际 2x2 块的 8bit 适配矩阵")


def onehot_check():
    heading("C. 辅助自旋与 one-hot 约束（2x2 实际块，32 个 Ising 状态）")
    V = np.array([[0.0, 3.0], [4.0, 0.0]])
    Q, offset, M = S.build_qubo(V)
    I, bias = S.to_ising(Q)
    n = Q.shape[0]
    nA = nB = 2
    rows = []
    for sb in itertools.product([-1, 1], repeat=I.shape[0]):
        s = np.array(sb, dtype=float)
        H = float(-s @ I @ s)
        x = ((s + 1) / 2).astype(int)
        bits = x[:nA + nB]
        valid = bits[:nA].sum() == 1 and bits[nA:].sum() == 1
        qv = float(x[:n] @ Q @ x[:n])
        rows.append((H, valid, tuple(bits), int(x[-1])))
    rows.sort()
    print("H 最小的 6 个状态（H, 合法, 前4位, aux位）:")
    for r in rows[:6]:
        print("  ", r)
    best_valid = min(r[0] for r in rows if r[1])
    best_invalid = min(r[0] for r in rows if not r[1])
    print(f"合法状态最优 H={best_valid:.3f} | 非法状态最优 H={best_invalid:.3f} | 罚项间隔={best_invalid-best_valid:.3f}")
    print(f"V 范围 [{V.min():.3f}, {V.max():.3f}] | M={M:.3f} | M > 范围: {M > V.max()-V.min()}")


def actual_q2():
    heading("D. 实际 Q2（topk=13）分辨率与返回解")
    A, B, V = S.load_pool("pool_q2_phys.csv", topk=13)
    Q, offset, M = S.build_qubo(V)
    I, bias = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    nA, nB = len(A), len(B)
    for name, Mx in (("原始 I", I), ("8bit adj", adj)):
        Aa = np.abs(Mx)
        top = Aa.max()
        obj = Aa[:nA, nA:nA + nB].max()
        step = top / 127
        print(f"{name}: shape={Mx.shape} max|J|={top:.3f} obj={obj:.3f} step={step:.5f} resol={obj/step:.3f} "
              f"diag_max={np.abs(np.diag(Mx)).max():.1e} sym={np.allclose(Mx, Mx.T)}")
    print(f"V range=[{V.min():.4f},{V.max():.4f}] M={M:.3f}")
    return A, B, V, I, adj


def resolution_q3():
    heading("E. 实际 Q3（topk=8，历史 k8_m1x 规模）分辨率")
    A, B, V = S.load_pool("pool_q3_phys.csv", topk=8)
    Q, offset, M = S.build_qubo(V)
    I, bias = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    nA, nB = len(A), len(B)
    for name, Mx in (("原始 I", I), ("8bit adj", adj)):
        Aa = np.abs(Mx)
        top = Aa.max()
        obj = Aa[:nA, nA:nA + nB].max()
        step = top / 127
        print(f"{name}: shape={Mx.shape} max|J|={top:.3f} obj={obj:.3f} step={step:.5f} resol={obj/step:.3f}")
    print(f"V range=[{V.min():.4f},{V.max():.4f}] M={M:.3f}")


identity_check()
sa_all()
onehot_check()
actual_q2()
resolution_q3()
