# -*- coding: utf-8 -*-
"""D 题 问题 2：QUBO → Ising（用 Kaiwu SDK 转换）→ SPQC 真机提交

两个必须先看懂的本地实测结论：
  1) QUBO 直接量化 8bit：最优解不变（max|Q|≈400，步长 3.15）
  2) 但硬件吃的是 Ising 矩阵，罚项对角项累积把 max|J| 放大到 ~2700，量化步长 21.6，
     而目标块系数只有 8.7 → 目标可分档数 0.40，等于被罚项淹没，真机上分不出候选差异
  3) 解法：代理模型先预筛 top-K，再上真机精排。K=13（26 比特）时目标可分档数 2.0，可用

用法：
  自检（不提交、不耗配额）：python d_submit_cim.py
  授权（只需一次）：        python d_submit_cim.py --init --user-id <ID> --sdk-code <CODE>
  真机（主线 K=13）：       python d_submit_cim.py --run --topk 13 --task-name apmcm_q2_no2_k13
"""
import argparse, os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
CODE = os.path.join(ROOT, "code")
os.makedirs(RES, exist_ok=True)


def load_pool(fname="pool_q2_phys.csv", topk=0):
    pool = pd.read_csv(os.path.join(CODE, fname))
    A = sorted(pool.A.unique()); B = sorted(pool.B.unique())
    V = np.zeros((len(A), len(B)))
    for _, r in pool.iterrows():
        V[A.index(r.A), B.index(r.B)] = r.V_hat
    if topk and topk < len(A):
        ia = np.argsort(V.min(1))[:topk]; ib = np.argsort(V.min(0))[:topk]
        A = [A[k] for k in ia]; B = [B[k] for k in ib]; V = V[np.ix_(ia, ib)]
    return A, B, V


def build_qubo(V, M=None):
    nA, nB = V.shape
    if M is None:
        M = float(max(2 * (V.max() - V.min()), 1.0) + 15)
    n = nA + nB
    Q = np.zeros((n, n)); Q[:nA, nA:] = V
    for base, k in [(0, nA), (nA, nB)]:
        for i in range(base, base + k):
            Q[i, i] -= M
            for j in range(i + 1, base + k):
                Q[i, j] += 2 * M
    return Q, 2 * M, M


def to_ising(Q):
    import kaiwu as kw
    I, bias = kw.core.qubo_matrix_to_ising_matrix(Q)
    return np.asarray(I, dtype=float), float(bias)


def resolution(I, nA, nB):
    """目标可分档数 = 目标块最大系数 / 量化步长"""
    A = np.abs(I)
    top = A.max()
    obj = A[:nA, nA:nA + nB].max()
    step = top / 127.0
    return dict(top=top, obj=obj, step=step, resol=obj / step)


def decode(bits, A, B):
    nA = len(A)
    ia = [i for i in range(nA) if bits[i] == 1]
    ib = [i - nA for i in range(nA, nA + len(B)) if bits[i] == 1]
    if len(ia) != 1 or len(ib) != 1:
        return None
    return A[ia[0]], B[ib[0]]


def analyse(topk=0, verbose=True):
    import kaiwu as kw
    import kaiwu.preprocess as pp
    A, B, V = load_pool(topk=topk)
    Q, offset, M = build_qubo(V)
    I, bias = to_ising(Q)
    r = resolution(I, len(A), len(B))
    i, j = np.unravel_index(V.argmin(), V.shape)
    # SDK 官方精度适配
    try:
        bw = pp.calculate_ising_matrix_bit_width(I, 8)
        dr = pp.get_dynamic_range_metric(I)
        adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    except Exception as e:
        bw, dr, adj = {"err": str(e)}, None, I
    if verbose:
        print(f"方案 topk={topk or '全量'}：{len(A)}×{len(B)} = {Q.shape[0]} 比特，M={M:.1f}")
        print(f"  QUBO max|Q|={np.abs(Q).max():.0f} | 穷举金标准 {A[i]}-{B[j]} V*={V[i,j]:.4f}")
        print(f"  Ising {I.shape} max|J|={r['top']:.0f} | 目标块 {r['obj']:.1f} | 步长 {r['step']:.2f}"
              f" | 目标可分档数 {r['resol']:.2f}")
        print(f"  SDK 精度适配: bit_width={bw} | dynamic_range={dr if dr is None else round(dr,2)}"
              f" | 8bit 整数矩阵 max={np.abs(adj).max():.0f}")
        flag = "可用" if r["resol"] >= 1.5 else ("勉强" if r["resol"] >= 1 else "不可用（目标被罚项淹没）")
        print(f"  → 8bit 分辨率判定：{flag}")
    return dict(A=A, B=B, V=V, Q=Q, I=I, adj=adj, bias=bias, M=M, res=r,
                gold=(A[i], B[j], float(V[i, j])))


def do_init(user_id="", sdk_code=""):
    """凭据只留本机：不带参数时走交互输入，不写进命令行历史"""
    import getpass
    import kaiwu.license as lic
    if not user_id:
        user_id = input("user_id: ").strip()
    if not sdk_code:
        sdk_code = getpass.getpass("sdk_code（输入时不显示）: ").strip()
    lic.init(user_id, sdk_code)
    print("license 已生成 → 可以 --run")


def do_run(task_name, project_no, sample_number, wait, topk, force):
    import kaiwu as kw
    from kaiwu.cim import CIMOptimizer, TaskMode
    info = analyse(topk=topk)
    if info["res"]["resol"] < 1 and not force:
        print("\n[中止] 目标可分档数 < 1，8bit 下目标项会被量化抹平，结果不可信。"
              "请用 --topk 13（或更小）或加 --force 强制提交。")
        return
    kw.license.verify_license(info["I"].shape[0])
    save = os.path.join(RES, "cim_tasks"); os.makedirs(save, exist_ok=True)
    kw.common.CheckpointManager.save_dir = save
    opt = CIMOptimizer(task_name=task_name, wait=wait, interval=6, project_no=project_no,
                       task_mode=TaskMode.OPTIMIZATION, sample_number=sample_number)
    sol = np.atleast_2d(np.asarray(opt.solve(info["adj"])))   # 提交 SDK 精度适配后的 8bit 整数矩阵
    print(f"返回 {len(sol)} 个解，形状 {sol.shape}")
    A, B, V = info["A"], info["B"], info["V"]
    bits_all = ((sol + 1) // 2).astype(int)
    rows = []
    for k in range(bits_all.shape[0]):
        bits = bits_all[k][:len(A) + len(B)]        # 丢掉 SDK 追加的辅助比特
        dd = decode(bits, A, B)
        rows.append(dict(sample=k, A=dd[0] if dd else "", B=dd[1] if dd else "",
                         V_hat=float(V[A.index(dd[0]), B.index(dd[1])]) if dd else np.nan,
                         valid=dd is not None))
    df = pd.DataFrame(rows)
    out = os.path.join(RES, f"{task_name}_result.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(df.to_string(index=False))
    print(f"\n穷举金标准 {info['gold'][0]}-{info['gold'][1]} V*={info['gold'][2]:.4f}")
    if df.valid.any():
        bt = df[df.valid].sort_values("V_hat").iloc[0]
        print(f"真机最优   {bt.A}-{bt.B} V*={bt.V_hat:.4f}"
              f"  → {'命中金标准 ✅' if (bt.A, bt.B) == info['gold'][:2] else '未命中 ⚠️'}")
    print("结果:", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--user-id", default=""); ap.add_argument("--sdk-code", default="")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--task-name", default="apmcm_q2_no2_k13")
    ap.add_argument("--project-no", default=None)
    ap.add_argument("--sample-number", type=int, default=10)
    ap.add_argument("--no-wait", action="store_true")
    ap.add_argument("--topk", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.init:
        do_init(a.user_id, a.sdk_code)
    elif a.run:
        do_run(a.task_name, a.project_no, a.sample_number, not a.no_wait, a.topk, a.force)
    else:
        for k in [0, 26, 13, 8]:
            analyse(k); print()
