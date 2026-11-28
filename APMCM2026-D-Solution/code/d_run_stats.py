# -*- coding: utf-8 -*-
"""真机统计实验：SAMPLING 多次采样 / 罚项倍数对照

安全约定：
  默认是 dry-run：只做本地建模与精度分析，不调用 license、不创建云端任务、不消耗配额。
  实际提交必须显式加 --submit，并在交互终端逐字输入任务名完成二次确认。

用法：
  python d_run_stats.py --task-name apmcm_q2_k13_samp200 --topk 13 --mode sampling --samples 200
  python d_run_stats.py --task-name apmcm_q2_k13_samp200 --topk 13 --mode sampling --samples 200 --submit
"""
import argparse, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import d_submit_cim as S
import precision_reducer as PRR
import kaiwu.preprocess as pp
from paths import CIM_SAMPLES, CIM_STATS, FIG, ensure_output_dirs
from experiment_archive import backup_if_exists, validate_spin_matrix

ensure_output_dirs()
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
RES = S.RES


def run(task_name, topk, mfactor, mode, samples, project_no=None, submit=False):
    A, B, V = S.load_pool(topk=topk)
    Q, offset, M0 = S.build_qubo(V)
    M = M0 * mfactor
    if mfactor != 1.0:
        Q, offset, M = S.build_qubo(V, M=M)
    I, bias = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
    nA, nB = len(A), len(B)
    Ir = np.abs(I)
    step_raw, obj_raw = Ir.max() / 127, Ir[:nA, nA:nA + nB].max()
    Ia = np.abs(adj)
    step = Ia.max() / 127
    obj = Ia[:nA, nA:nA + nB].max()
    i0, j0 = np.unravel_index(V.argmin(), V.shape)
    gold = (A[i0], B[j0], float(V[i0, j0]))
    print(f"[{task_name}] {nA}×{nB} -> Ising {adj.shape} | M={M:.1f}（基准 {M0:.1f} × {mfactor}）")
    print(f"  原始 Ising：max|J|={Ir.max():.0f} | 目标块 {obj_raw:.2f} | 步长 {step_raw:.2f}"
          f" | 目标可分档数 {obj_raw/step_raw:.2f}")
    print(f"  8bit 适配后：max|J|={Ia.max():.0f} | 目标块 {obj:.2f} | 步长 {step:.2f}"
          f" | 目标可分档数 {obj/step:.2f}")
    print(f"  代理模型矩阵最优 {gold[0]}-{gold[1]} V*={gold[2]:.4f} | 模式 {mode} 采样 {samples}")

    if not submit:
        print("\n[DRY-RUN] 已完成本地建模与精度分析；未调用 license、未创建云端任务、未消耗配额。")
        print(f"          若确认提交，请追加 --submit，并在提示处逐字输入任务名 {task_name}。")
        return dict(task=task_name, mode=mode, samples=None, mfactor=mfactor,
                    sample_number_param=int(samples), returned_solutions=None,
                    M=M, maxJ=float(Ia.max()), step=float(step), obj=float(obj),
                    resol=float(obj / step), resol_raw=float(obj_raw / step_raw),
                    resol_adj=float(obj / step),
                    h_direction="lower_is_better",
                    gold=f"{gold[0]}-{gold[1]}", gold_V=gold[2],
                    submitted=False)

    if not S.confirm_submit(task_name, Q.shape[0], adj.shape[0], mode,
                            max(int(samples), 10)):
        return dict(task=task_name, submitted=False, reason="user_cancelled")

    import kaiwu as kw
    from kaiwu.cim import CIMOptimizer, TaskMode
    kw.license.verify_license(adj.shape[0])
    save = RES / "cim_tasks"; save.mkdir(parents=True, exist_ok=True)
    kw.common.CheckpointManager.save_dir = str(save)
    tm = TaskMode.SAMPLING if mode == "sampling" else TaskMode.OPTIMIZATION
    opt = CIMOptimizer(task_name=task_name, wait=True, interval=6, project_no=project_no,
                       task_mode=tm, sample_number=max(int(samples), 10))
    sol = np.atleast_2d(np.asarray(opt.solve(adj)))
    try:
        sol = validate_spin_matrix(sol, adj.shape[0])
    except ValueError as exc:
        raise SystemExit(f"[中止] 返回解格式异常：{exc}；未写入统计与逐样本文件。")
    print(f"  返回 {sol.shape[0]} 个解 × {sol.shape[1]} 比特")

    rows = []
    for k in range(sol.shape[0]):
        s = sol[k].astype(float)
        H = float(-s @ adj @ s)                     # QBoson 报告里的 Hamiltonian 约定
        bits = PRR.logical_bits_from_spins(s)[0][:nA + nB]
        ai = [i for i in range(nA) if bits[i] == 1]
        bi = [i - nA for i in range(nA, nA + nB) if bits[i] == 1]
        ok = len(ai) == 1 and len(bi) == 1
        rows.append(dict(sample=k, H=H, valid=ok,
                         A=A[ai[0]] if ok else "", B=B[bi[0]] if ok else "",
                         formula=f"{A[ai[0]]}{B[bi[0]]}O2N" if ok else "",
                         V_hat=float(V[ai[0], bi[0]]) if ok else np.nan))
    df = pd.DataFrame(rows)
    valid = df[df.valid]
    def rank_of(r):
        idx = (A.index(r.A), B.index(r.B))
        return int((V < V[idx]).sum()) + 1
    hit8 = sum(1 for _, r in valid.iterrows() if rank_of(r) <= 8)
    stats = dict(task=task_name, mode=mode, samples=int(sol.shape[0]),
                 sample_number_param=int(samples), returned_solutions=int(sol.shape[0]),
                 mfactor=mfactor,
                 M=M, maxJ=float(Ia.max()), step=float(step), obj=float(obj), resol=float(obj / step),
                 resol_raw=float(obj_raw / step_raw), resol_adj=float(obj / step),
                 h_direction="lower_is_better",
                 n_valid=int(valid.shape[0]), valid_rate=round(float(valid.shape[0] / len(df)), 4),
                 best_V=float(valid.V_hat.min()) if len(valid) else None,
                 best_formula=(valid.sort_values("V_hat").iloc[0].formula if len(valid) else ""),
                 best_rank=(rank_of(valid.sort_values("V_hat").iloc[0]) if len(valid) else None),
                 gold=f"{gold[0]}-{gold[1]}", gold_V=gold[2],
                 hit_top8=hit8, H_min=float(df.H.min()), H_max=float(df.H.max()),
                 H_median=float(df.H.median()))
    print("\n" + pd.DataFrame([stats]).T.to_string(header=False))
    samples_path = CIM_SAMPLES / f"{task_name}_samples.csv"
    stats_path = CIM_STATS / f"{task_name}_stats.json"
    fig_path = FIG / f"{task_name}_H_hist.png"
    for p in (samples_path, stats_path, fig_path):
        backup = backup_if_exists(p)
        if backup:
            print(f"[提示] 旧文件已备份：{backup}")
    df.sort_values("H", ascending=True).to_csv(samples_path,
                                               index=False, encoding="utf-8-sig")
    json.dump(stats, open(stats_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # H 分布图
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.hist(df.H, bins=40, color="#2E7D8F")
    ax.set_xlabel("Hamiltonian（越小越好，按 H = -sᵀJs）"); ax.set_ylabel("解个数")
    ax.set_title(f"{task_name}：{len(df)} 个采样解的 Hamiltonian 分布")
    fig.tight_layout(); fig.savefig(fig_path, dpi=200); plt.close(fig)
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-name", required=True)
    ap.add_argument("--topk", type=int, default=13)
    ap.add_argument("--mode", choices=["sampling", "opt"], default="sampling")
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--mfactor", type=float, default=1.0)
    ap.add_argument("--project-no", default=None)
    ap.add_argument("--submit", action="store_true",
                    help="实际提交真机任务（需交互二次确认，消耗配额）")
    ap.add_argument("--dry-run", action="store_true",
                    help="仅本地分析，不提交（默认行为，显式声明用）")
    a = ap.parse_args()
    if a.submit and a.dry_run:
        raise SystemExit("[中止] --submit 与 --dry-run 不能同时使用。")
    run(a.task_name, a.topk, a.mfactor, a.mode, a.samples, a.project_no, submit=a.submit)
