# -*- coding: utf-8 -*-
"""Phase 10：正式实验执行入口（输入版本 → 配额/去重检查 → 人工确认 → 归档）。

安全约定：
1. 默认 dry-run，不调用 license、不创建云端任务、不消耗配额。
2. 实际提交必须显式 ``--submit``，并逐字输入任务编号完成人工确认。
3. 不提供设备选择参数：设备由平台调度，SDK 不支持指定机型。
4. 不接收任何凭据参数；授权只走 ``d_submit_cim.py --init`` 的交互输入。
5. 失败按阶段区分为 submit / run / download，便于恢复与追责。
6. 只归档原始返回，不重算、不替换参赛队员的科学结论。

用法示例：
    python code/d_experiment.py inputs register --version team_q2_v1 \
        --matrix code/predictions/pool_q2_phys.csv --format long --sub-q Q2 --x NO2
    python code/d_experiment.py inputs list
    python code/d_experiment.py plan --input-version team_q2_v1 --task-name q2_k13 --topk 13
    python code/d_experiment.py run  --input-version team_q2_v1 --task-name q2_k13 --topk 13
    python code/d_experiment.py run  --input-version team_q2_v1 --task-name q2_k13 --topk 13 --submit
    python code/d_experiment.py status
    python code/d_experiment.py resume --task-id <task_id>
    python code/d_experiment.py attach-report --task-id <task_id> --file <pdf> --device SPQC-550
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import URLError

import numpy as np

import d_submit_cim as S
import experiment_budget as budget
import experiment_input as exin_mod
from experiment_archive import (
    Registry,
    STATUS_TEXT,
    TaskArchive,
    make_task_id,
    now_str,
    validate_spin_matrix,
)
from experiment_input import ExperimentInput, numeric_matrix_sha256
from paths import ROOT

EXIT_OK = 0
EXIT_BLOCKED = 2
EXIT_FAILED = 3


# ---------------------------------------------------------------------------
# 建模辅助（复用 d_submit_cim 的既有函数，不改变任何模型设定）
# ---------------------------------------------------------------------------
def select_topk(A, B, V, topk: int):
    if topk and topk < len(A):
        ia = np.argsort(V.min(1))[:topk]
        ib = np.argsort(V.min(0))[:topk]
        return [A[i] for i in ia], [B[i] for i in ib], V[np.ix_(ia, ib)]
    return list(A), list(B), V


def build_problem(exin: ExperimentInput, topk: int = 0, mfactor: float = 1.0) -> dict:
    """构造 QUBO / Ising / 8bit 精度适配矩阵；只复用既有实现。"""
    import kaiwu.preprocess as pp

    A, B, V = select_topk(exin.A, exin.B, exin.V, topk)
    Q, offset, M0 = S.build_qubo(V)
    M = M0
    if mfactor != 1.0:
        Q, offset, M = S.build_qubo(V, M=M0 * mfactor)
    I, bias = S.to_ising(Q)
    adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)

    nA, nB = len(A), len(B)
    raw = S.resolution(I, nA, nB)
    Ia = np.abs(adj)
    step = Ia.max() / 127.0 if Ia.max() else 1.0
    obj = Ia[:nA, nA:nA + nB].max() if nA and nB else 0.0
    adj_resol = float(obj / step)
    n_qubo = int(Q.shape[0])
    n_ising = int(adj.shape[0])
    return {
        "A": A, "B": B, "V": V, "Q": Q, "I": I, "adj": adj,
        "offset": float(offset), "bias": float(bias), "M": float(M), "M0": float(M0),
        "topk": int(topk), "mfactor": float(mfactor),
        "n_qubo": n_qubo, "n_ising": n_ising,
        "aux_bits": n_ising - n_qubo,
        "resol_raw": float(raw["resol"]), "resol_adj": adj_resol,
        "maxJ": float(Ia.max()), "obj_adj": float(obj), "step_adj": float(step),
        "matrix_sha256": numeric_matrix_sha256(adj),
    }


def validate_run_args(mode: str, topk: int, n_labels: int, samples: int):
    """本地参数校验：避免把明显非法的规模送到 SDK。"""
    if topk < 0:
        raise SystemExit(f"[参数] --topk 不能为负：{topk}")
    if topk and topk > n_labels:
        raise SystemExit(f"[参数] --topk={topk} 超过可用标签数 {n_labels}")
    if mode not in ("opt", "sampling"):
        raise SystemExit(f"[参数] 未知模式：{mode}")
    if not (10 <= int(samples) <= 2000):
        raise SystemExit(f"[参数] --samples 必须在 10..2000（SDK 限制）：{samples}")


def _prepare_backend(task_name: str, mode: str, samples: int, backend: str,
                     arc: TaskArchive, problem: dict, project_no: str = None,
                     mock_fail_stage: str = None):
    """构造后端；与 solve 分开，便于把授权/构造失败归档为提交失败。"""
    if backend == "mock":
        from mock_backend import MockCIMOptimizer
        opt = MockCIMOptimizer(task_name=task_name, wait=True, interval=6, project_no=project_no,
                               task_mode="sampling" if mode == "sampling" else "optimization",
                               sample_number=max(int(samples), 10),
                               fail_stage=mock_fail_stage)
        return opt, None

    import kaiwu as kw
    kw.license.verify_license(problem["n_ising"])
    opt = _make_real_optimizer(task_name, mode, samples,
                               arc.dir / "sdk_checkpoints", project_no)
    sdk_hash = None
    try:
        sdk_hash = opt._ising_to_md5_hash(problem["adj"])
    except Exception as e:
        arc.log(f"[WARN] 无法获取 SDK 矩阵哈希：{e}")
    return opt, sdk_hash


def print_plan(exin, problem, task_name, mode, samples, submit, dup, budget_info, task_id):
    print("=" * 66)
    print(f"输入版本      : {exin.version}（{exin.kind}）")
    print(f"来源说明      : {exin_mod.INPUT_KINDS.get(exin.kind)}")
    print(f"输入矩阵哈希  : {exin.matrix_sha256}")
    print(f"矩阵规模      : {exin.shape[0]}×{exin.shape[1]}"
          + (f"（topk={problem['topk']} 预筛后）" if problem["topk"] else ""))
    print(f"QUBO / Ising  : {problem['n_qubo']} 比特 → {problem['n_ising']} 比特"
          f"（辅助自旋 {problem['aux_bits']} 个，位于末位）")
    print(f"罚项 M        : {problem['M']:.3f}（基准 {problem['M0']:.3f} × {problem['mfactor']:g}）")
    print(f"目标分辨率    : 原始 Ising {problem['resol_raw']:.2f} 档 | "
          f"8bit 适配后 {problem['resol_adj']:.2f} 档（两种口径同时给出）")
    print(f"实际提交矩阵  : sha256={problem['matrix_sha256'][:16]}…  shape={problem['n_ising']}×{problem['n_ising']}")
    print(f"模式          : {mode} | 采样数 {samples}")
    print(f"设备          : 由平台调度（SDK 不支持指定机型）")
    print(f"本地配额      : {budget_info['label']} 总额 {budget_info['total']} / "
          f"已用 {budget_info['used']} / 剩余 {budget_info['remaining']}"
          f"（verified={budget_info['verified']}，{budget_info['source']}）")
    if dup:
        t, why = dup
        print(f"重复检查      : 命中历史任务 {t['task_id']}（{why}，状态 {t.get('status')}）")
    else:
        print("重复检查      : 未发现同矩阵历史任务")
    print(f"任务编号      : {task_id}（{'提交时生成' if submit else '预演，不落盘'}）")
    print("=" * 66)


# ---------------------------------------------------------------------------
# 失败阶段判定
# ---------------------------------------------------------------------------
def classify_error(exc: BaseException, tb_text: str = "") -> str:
    """返回 submit / run / download / unknown。依据 SDK 1.4.4 实际报错文本。"""
    msg = str(exc)
    blob = f"{msg}\n{tb_text}"
    if "Task creation failed" in blob or "Network error during task creation" in blob \
            or "Network error during file upload" in blob or "Unexpected error during file upload" in blob:
        return "submit"
    if isinstance(exc, URLError) or "read_pickle" in blob or "SSL" in blob \
            or "Task completed but no result URL" in blob or "Request error" in blob:
        return "download"
    if "Task run failed" in blob or "Task failed" in blob or "task_status_code" in blob:
        return "run"
    return "unknown"


def _traceback_text() -> str:
    import traceback
    return "".join(traceback.format_exc())


# ---------------------------------------------------------------------------
# 确认
# ---------------------------------------------------------------------------
def interactive_confirm(task_id: str, task_name: str, input_version: str, mode: str,
                        n_ising: int, budget_info: dict) -> bool:
    print("\n" + "!" * 66)
    print("真机提交确认：确认后将创建云端任务并消耗配额")
    print(f"  任务编号 : {task_id}")
    print(f"  任务名称 : {task_name}")
    print(f"  输入版本 : {input_version}")
    print(f"  计算模式 : {mode}")
    print(f"  矩阵规模 : Ising {n_ising}×{n_ising}（含辅助自旋）")
    print(f"  本地配额 : 剩余 {budget_info['remaining']} 次，本次消耗 1 次")
    print("  设备型号 : 由平台调度（SDK 不支持指定机型）")
    print("!" * 66)
    if not sys.stdin.isatty():
        print("[中止] 当前不是交互终端，无法完成人工确认。")
        return False
    try:
        answer = input(f"请逐字输入任务编号 {task_id} 确认提交（其他输入取消）: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[中止] 未获得确认，未提交任务。")
        return False
    if answer != task_id:
        print("[中止] 确认文本不匹配，未提交任务。")
        return False
    return True


# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------
def _make_real_optimizer(task_name: str, mode: str, samples: int, save_dir: Path,
                         project_no: str = None):
    import kaiwu as kw
    from kaiwu.cim import CIMOptimizer, TaskMode

    kw.common.CheckpointManager.save_dir = str(save_dir)
    task_mode = TaskMode.SAMPLING if mode == "sampling" else TaskMode.OPTIMIZATION
    opt = CIMOptimizer(task_name=task_name, wait=True, interval=6, project_no=project_no,
                       task_mode=task_mode, sample_number=max(int(samples), 10))
    return opt


def execute_task(input_version: str, task_name: str, mode: str = "opt", topk: int = 0,
                 mfactor: float = 1.0, samples: int = 10, submit: bool = False,
                 backend: str = "real", mock_fail_stage: str = None,
                 allow_matrix_reuse: bool = False, confirm=None,
                 project_no: str = None, notes: str = "") -> dict:
    """执行一次实验（默认 dry-run）。返回结构化结果，便于测试与审计。"""
    exin = exin_mod.load(input_version)
    validate_run_args(mode, topk, len(exin.A), samples)
    problem = build_problem(exin, topk=topk, mfactor=mfactor)
    registry = Registry()
    mode_key = budget.mode_key(mode)
    b_info = budget.available(mode, registry)

    dup, dup_reason = registry.find_duplicate(task_name, problem["matrix_sha256"])
    prospective_id = make_task_id(task_name, problem["matrix_sha256"], registry)

    print_plan(exin, problem, task_name, mode, samples, submit, (dup, dup_reason) if dup else None,
               b_info, prospective_id)

    base = {
        "task_id": None, "task_name": task_name, "input_version": exin.version,
        "input_kind": exin.kind, "matrix_sha256": problem["matrix_sha256"],
        "status": "dry_run", "submitted": False, "archive_dir": None,
        "backend": backend,
    }

    if not submit:
        print("\n[DRY-RUN] 未调用 license、未创建云端任务、未消耗配额、未写入归档。")
        print("          确认要提交时追加 --submit，并按提示输入任务编号。")
        base["next_task_id"] = prospective_id
        return base

    # ---- 提交前拦截 ----
    if dup:
        t, why = dup, dup_reason
        if why == "task_name_and_matrix":
            raise SystemExit(
                f"[重复拦截] 任务名 {task_name} 与同一矩阵已存在：{t['task_id']}（{t.get('status')}）。\n"
                f"查询/恢复结果请用：python code/d_experiment.py resume --task-id {t['task_id']}"
            )
        if not allow_matrix_reuse:
            raise SystemExit(
                f"[重复拦截] 同一矩阵已提交过：{t['task_id']}（任务名 {t.get('task_name')}）。\n"
                "重复提交会再消耗 1 次配额。确需重跑请加 --allow-matrix-reuse 并换任务名。"
            )

    b_info = budget.check(mode, 1, registry)

    task_id = prospective_id
    if confirm is None:
        ok = interactive_confirm(task_id, task_name, exin.version, mode,
                                 problem["n_ising"], b_info)
    else:
        ok = bool(confirm)
    if not ok:
        print("[取消] 用户未确认，未提交任务。")
        base.update({"status": "cancelled"})
        return base

    config = {
        "task_name": task_name,
        "mode": mode,
        "mode_key": mode_key,
        "task_mode": "sampling" if mode == "sampling" else "optimization",
        "topk": int(topk),
        "mfactor": float(mfactor),
        "samples": int(samples),
        "project_no": project_no,
        "quota_units": 1,
        "backend": backend,
        "notes": notes,
        "n_qubo": problem["n_qubo"],
        "n_ising": problem["n_ising"],
        "aux_bits": problem["aux_bits"],
        "M": problem["M"],
        "M0": problem["M0"],
        "resol_raw": problem["resol_raw"],
        "resol_adj": problem["resol_adj"],
        "ising_matrix_sha256": problem["matrix_sha256"],
        "git_dir": str(ROOT),
        "started_at": now_str(),
    }
    arc = TaskArchive.create(task_id, config, exin, problem["adj"],
                             raw_ising_matrix=problem["I"])
    entry = {k: arc.meta()[k] for k in (
        "task_id", "task_name", "status", "input_version", "input_kind",
        "input_matrix_sha256", "submitted_matrix_sha256", "mode_key", "mode",
        "quota_units", "archive_dir")}
    entry.update({"created_at": arc.meta()["created_at"], "updated_at": now_str()})
    registry.add(entry)

    base.update({"task_id": task_id, "archive_dir": str(arc.dir), "status": "created"})
    arc.log(f"创建任务归档 {task_id}（输入 {exin.version}，kind={exin.kind}）")
    arc.append_attempt("submit", "started", f"backend={backend}")

    # ---- 后端起任务 ----
    try:
        opt, sdk_hash = _prepare_backend(task_name, mode, samples, backend, arc, problem,
                                         project_no, mock_fail_stage)
    except BaseException as exc:  # noqa: BLE001 - 授权/构造失败按提交失败归档
        stage = classify_error(exc, _traceback_text())
        arc.log(f"[失败] 后端准备阶段 {stage} 类型={type(exc).__name__}：{exc}")
        arc.append_attempt("prepare", "failed", str(exc), error_type=type(exc).__name__)
        arc.update(status="submit_failed", error_stage=f"prepare:{stage}",
                   error_type=type(exc).__name__, error_message=str(exc), quota_counted=False)
        registry.update(task_id, status="submit_failed", quota_counted=False,
                        error_stage=f"prepare:{stage}")
        base.update({"status": "submit_failed", "error_stage": f"prepare:{stage}",
                     "error": str(exc)})
        print(f"\n[失败] 后端准备失败（未创建云端任务）：{type(exc).__name__}: {exc}")
        print(f"       归档：{arc.dir}")
        print("       该状态不计配额，可用同一任务名重新提交。")
        return base

    if sdk_hash:
        arc.update(sdk_matrix_hash=sdk_hash)
        registry.update(task_id, sdk_matrix_hash=sdk_hash)

    t0 = time.perf_counter()
    try:
        solutions = opt.solve(problem["adj"])
    except KeyboardInterrupt:
        elapsed = time.perf_counter() - t0
        arc.log("[中断] 进程在提交后被中断；云端任务可能已创建，请用 resume 查询，勿重复提交。")
        arc.append_attempt("solve", "interrupted", "KeyboardInterrupt", runtime_s=elapsed)
        arc.update(status="submitted", error_stage="interrupted",
                   error_type="KeyboardInterrupt",
                   error_message="进程在提交后被中断", runtime_s=round(elapsed, 3),
                   quota_counted=True)
        registry.update(task_id, status="submitted", quota_counted=True,
                        error_stage="interrupted")
        base.update({"status": "submitted", "submitted": True})
        return base
    except BaseException as exc:  # noqa: BLE001 - 需要按阶段归档所有失败
        elapsed = time.perf_counter() - t0
        stage = classify_error(exc, _traceback_text())
        status = {"submit": "submit_failed", "run": "run_failed",
                  "download": "download_failed"}.get(stage, "unknown_failure")
        counted = status != "submit_failed"
        arc.log(f"[失败] 阶段={stage} 类型={type(exc).__name__}：{exc}")
        arc.append_attempt(stage, "failed", str(exc), error_type=type(exc).__name__,
                           runtime_s=elapsed)
        arc.update(status=status, error_stage=stage, error_type=type(exc).__name__,
                   error_message=str(exc), runtime_s=round(elapsed, 3), quota_counted=counted)
        registry.update(task_id, status=status, quota_counted=counted, error_stage=stage)
        base.update({"status": status, "error_stage": stage, "error": str(exc)})
        print(f"\n[失败] 阶段 {stage} / 状态 {status} / {type(exc).__name__}: {exc}")
        print(f"       归档：{arc.dir}")
        if status == "download_failed":
            print("       任务可能已完成，请用 resume 重新取回结果，勿重新提交。")
        return base

    elapsed = time.perf_counter() - t0
    try:
        arr = validate_spin_matrix(solutions, problem["n_ising"])
    except ValueError as exc:
        raw = np.atleast_2d(np.asarray(solutions))
        arc.save_solutions(raw)
        arc.log(f"[非法返回] {exc}；原始数组已保存，未采信。")
        arc.append_attempt("result", "invalid", str(exc), shape=list(raw.shape),
                           runtime_s=elapsed)
        arc.update(status="invalid_result", error_stage="result",
                   error_type="ValueError", error_message=str(exc),
                   returned_solutions=list(raw.shape), runtime_s=round(elapsed, 3),
                   quota_counted=True)
        registry.update(task_id, status="invalid_result", quota_counted=True,
                        error_stage="result")
        base.update({"status": "invalid_result", "error_stage": "result", "error": str(exc)})
        print(f"\n[失败] 返回解格式非法：{exc}")
        print(f"       原始数组已归档：{arc.dir}")
        return base

    arc.save_solutions(arr)
    arc.save_energy(arr, problem["adj"])
    arc.log(f"提交成功，返回 {arr.shape[0]} 个解 × {arr.shape[1]} 比特，耗时 {elapsed:.2f}s")
    arc.append_attempt("solve", "completed", f"solutions={arr.shape}", runtime_s=elapsed)
    arc.update(status="completed", returned_solutions=list(arr.shape),
               runtime_s=round(elapsed, 3), quota_counted=True, completed_at=now_str())
    registry.update(task_id, status="completed", quota_counted=True,
                    returned_solutions=list(arr.shape))
    base.update({"status": "completed", "submitted": True, "solutions": list(arr.shape)})
    print(f"\n[完成] 原始解已归档：{arc.dir / 'raw' / 'solutions.npz'}")
    print(f"       归档目录：{arc.dir}")
    return base


# ---------------------------------------------------------------------------
# 恢复 / 查询
# ---------------------------------------------------------------------------
def resume_task(task_id: str, backend=None, local_only: bool = False) -> dict:
    """用同一任务名 + 同一矩阵向平台查询已有结果；绝不重新提交。"""
    arc = TaskArchive(task_id)
    meta = arc.meta()
    if local_only:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return {"task_id": task_id, "status": meta.get("status"), "local_only": True}
    matrix_path = arc.dir / "input" / "ising_matrix.csv"
    if not matrix_path.is_file():
        raise SystemExit(f"[恢复] 归档缺少实际提交矩阵：{matrix_path}")
    adj = np.loadtxt(matrix_path, delimiter=",")
    if meta.get("status") not in ("submitted", "download_failed", "run_failed",
                                  "unknown_failure", "invalid_result", "resume_no_result",
                                  "completed", "created"):
        raise SystemExit(f"[恢复] 当前状态 {meta.get('status')} 不支持恢复。")

    if backend is None:
        import kaiwu as kw
        kw.license.verify_license(adj.shape[0])
        backend = _make_real_optimizer(meta["task_name"], meta.get("mode", "opt"),
                                       meta.get("samples") or 10,
                                       arc.dir / "sdk_checkpoints", meta.get("project_no"))

    arc.log(f"尝试恢复任务 {task_id}（仅查询，不重新提交）")
    arc.append_attempt("resume", "started", type(backend).__name__)

    try:
        result = backend.get_task_result(adj)
    except BaseException as exc:  # noqa: BLE001
        stage = classify_error(exc, _traceback_text())
        status = "download_failed" if stage == "download" else (
            "run_failed" if stage == "run" else "resume_no_result")
        arc.append_attempt("resume", "failed", str(exc), error_type=type(exc).__name__)
        arc.update(status=status, error_stage=stage, error_type=type(exc).__name__,
                   error_message=str(exc))
        Registry().update(task_id, status=status, error_stage=stage)
        print(f"[恢复失败] 阶段 {stage} / {type(exc).__name__}: {exc}")
        return {"task_id": task_id, "status": status, "error": str(exc)}

    arc.save_platform_result(result)
    solutions = None
    if isinstance(result, dict):
        raw = result.get("solutions")
        if raw is None:
            raw = result.get("result")
        if raw is not None:
            try:
                solutions = np.atleast_2d(np.asarray(raw))
            except Exception:
                solutions = None

    if solutions is not None and solutions.size:
        try:
            solutions = validate_spin_matrix(solutions, adj.shape[0])
        except ValueError as exc:
            arc.update(status="invalid_result", error_stage="result",
                       error_type="ValueError", error_message=str(exc))
            Registry().update(task_id, status="invalid_result", error_stage="result")
            print(f"[恢复] 平台返回解格式非法：{exc}；原始返回已归档。")
            return {"task_id": task_id, "status": "invalid_result", "error": str(exc)}
        if not (arc.dir / "raw" / "solutions.npz").exists():
            arc.save_solutions(solutions)
            arc.save_energy(solutions, adj)
        arc.update(status="completed", returned_solutions=list(solutions.shape),
                   completed_at=now_str(), quota_counted=True)
        Registry().update(task_id, status="completed", quota_counted=True)
        print(f"[恢复完成] 已取回 {solutions.shape[0]} 个解 × {solutions.shape[1]} 比特")
        return {"task_id": task_id, "status": "completed", "solutions": list(solutions.shape)}

    status = "run_failed" if (isinstance(result, dict) and
                              str(result.get("task_status_code", "")).upper() in ("FAILED", "FAIL")) \
        else "resume_no_result"
    arc.update(status=status)
    Registry().update(task_id, status=status)
    print(f"[恢复] 未取到解，状态记为 {status}；平台返回已原样归档。")
    return {"task_id": task_id, "status": status, "platform_result": result}


def remote_status(task_id: str) -> dict:
    """尝试用 SDK 私有接口查询任务状态（best-effort，可能不兼容未来版本）。"""
    arc = TaskArchive(task_id)
    meta = arc.meta()
    if not meta.get("sdk_matrix_hash"):
        raise SystemExit("[查询] 归档中没有 SDK 矩阵哈希，无法远程查询。")
    import kaiwu as kw
    backend = _make_real_optimizer(meta["task_name"], meta.get("mode", "opt"),
                                   meta.get("samples") or 10, arc.dir / "sdk_checkpoints",
                                   meta.get("project_no"))
    fn = getattr(backend, "_query_task_status", None)
    if fn is None:
        raise SystemExit("[查询] 当前 SDK 版本不提供任务状态查询接口。")
    res = fn(meta["task_name"], meta["sdk_matrix_hash"])
    arc.save_platform_result({"source": "_query_task_status", "response": res})
    return {"task_id": task_id, "response": res}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def cmd_inputs_register(a):
    fmt = a.format
    if fmt == "auto":
        fmt = "matrix" if a.matrix.lower().endswith(".npz") else "long"
    vdir = exin_mod.register(
        version=a.version, matrix_path=Path(a.matrix), fmt=fmt, kind=a.kind,
        value_col=a.value_col, a_col=a.a_col, b_col=a.b_col, x_col=a.x_col, x_value=a.x,
        notes=a.notes or "", sub_question=a.sub_q or "", value_semantics=a.value_semantics,
    )
    m = json.loads((vdir / "manifest.json").read_text(encoding="utf-8"))
    print(f"[已登记] {m['version']}  kind={m['kind']}  shape={m['shape']}")
    print(f"  matrix_sha256 = {m['matrix_sha256']}")
    for k, v in m["files"].items():
        print(f"  {k}: {v}")
    return EXIT_OK


def cmd_inputs_list(a):
    rows = exin_mod.list_versions()
    if not rows:
        print(f"[输入] 尚无已登记版本（目录 {exin_mod.inputs_root()}）")
        return EXIT_OK
    print(f"{'version':24s} {'kind':26s} {'shape':10s} {'created_at':22s} sha256")
    for r in rows:
        print(f"{r.get('version',''):24s} {str(r.get('kind','')):26s} "
              f"{str(r.get('shape','')):10s} {str(r.get('created_at','')):22s} "
              f"{str(r.get('matrix_sha256',''))[:16]}")
    return EXIT_OK


def cmd_inputs_show(a):
    e = exin_mod.load(a.version)
    print(json.dumps({
        "version": e.version, "kind": e.kind, "shape": list(e.shape),
        "matrix_sha256": e.matrix_sha256, "files": e.files,
        "sub_question": e.sub_question, "x_value": e.x_value,
        "value_column": e.value_column, "value_semantics": e.value_semantics,
        "source_paths": e.source_paths, "notes": e.notes,
        "A": e.A[:5] + (["…"] if len(e.A) > 5 else []),
        "B": e.B[:5] + (["…"] if len(e.B) > 5 else []),
    }, ensure_ascii=False, indent=2))
    return EXIT_OK


def cmd_plan(a):
    r = execute_task(a.input_version, a.task_name, a.mode, a.topk, a.mfactor, a.samples,
                     submit=False, backend=a.backend)
    return EXIT_OK if r.get("status") == "dry_run" else EXIT_BLOCKED


def cmd_run(a):
    r = execute_task(a.input_version, a.task_name, a.mode, a.topk, a.mfactor, a.samples,
                     submit=a.submit, backend=a.backend, mock_fail_stage=a.mock_fail_stage,
                     allow_matrix_reuse=a.allow_matrix_reuse, project_no=a.project_no)
    if r.get("status") in ("dry_run", "completed", "submitted", "cancelled"):
        return EXIT_OK
    return EXIT_FAILED


def cmd_status(a):
    reg = Registry()
    if a.task_id:
        arc = TaskArchive(a.task_id)
        meta = arc.meta()
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        att = arc.dir / "attempts.jsonl"
        if att.is_file():
            print("\n尝试记录：")
            print(att.read_text(encoding="utf-8").strip())
        if a.remote:
            print("\n远程状态（best-effort）：")
            print(json.dumps(remote_status(a.task_id), ensure_ascii=False, indent=2, default=str))
        return EXIT_OK
    if not reg.tasks:
        print("[任务] 本地注册表为空")
        return EXIT_OK
    print(f"{'task_id':44s} {'status':16s} {'input':20s} quota")
    for t in reg.tasks:
        print(f"{t.get('task_id',''):44s} {str(t.get('status','')):16s} "
              f"{str(t.get('input_version','')):20s} "
              f"{'是' if t.get('quota_counted') else '否'}")
    print("\n状态说明：")
    for k, v in STATUS_TEXT.items():
        print(f"  {k:18s} {v}")
    return EXIT_OK


def cmd_resume(a):
    r = resume_task(a.task_id, local_only=a.local_only)
    return EXIT_OK if r.get("status") == "completed" else EXIT_FAILED


def cmd_attach(a):
    arc = TaskArchive(a.task_id)
    meta = arc.attach_report(Path(a.file), device=a.device, platform_task_id=a.platform_task_id,
                             hardware_ms=a.hardware_ms)
    print(f"[已归档] 报告 {Path(a.file).name} → {meta['report_file']}")
    print(f"  报告 SHA256 = {meta['report_sha256']}")
    if a.device:
        print(f"  设备（来自平台报告）= {a.device}")
    if a.hardware_ms is not None:
        print(f"  硬件耗时（来自平台报告）= {a.hardware_ms} ms")
    return EXIT_OK


def cmd_budget(a):
    reg = Registry()
    for mode in ("optimization", "sampling"):
        info = budget.available(mode, reg)
        print(f"{info['label']}: 总额 {info['total']} / 已用 {info['used']} / "
              f"剩余 {info['remaining']} | verified={info['verified']} | 来源 {info['source']}")
    print(f"\n预算文件：{budget.budget_path()}")
    print("注意：这是本地账本，不能替代平台余额核对。")
    return EXIT_OK


def build_parser():
    ap = argparse.ArgumentParser(description="APMCM D 题正式实验执行入口（默认 dry-run）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inputs", help="实验输入版本管理")
    s2 = p.add_subparsers(dest="inputs_cmd", required=True)

    pr = s2.add_parser("register", help="登记新的输入版本（冻结 + SHA256）")
    pr.add_argument("--version", required=True)
    pr.add_argument("--matrix", required=True)
    pr.add_argument("--format", choices=["auto", "matrix", "long"], default="auto")
    pr.add_argument("--kind", choices=sorted(exin_mod.INPUT_KINDS), default=None)
    pr.add_argument("--value-col", default="V_hat")
    pr.add_argument("--a-col", default="A")
    pr.add_argument("--b-col", default="B")
    pr.add_argument("--x-col", default=None)
    pr.add_argument("--x", default=None)
    pr.add_argument("--sub-q", default=None)
    pr.add_argument("--value-semantics", default="lower_is_better",
                    choices=["lower_is_better", "higher_is_better"])
    pr.add_argument("--notes", default=None)
    pr.set_defaults(func=cmd_inputs_register)

    pl = s2.add_parser("list", help="列出已登记版本")
    pl.set_defaults(func=cmd_inputs_list)

    ps = s2.add_parser("show", help="查看某个版本")
    ps.add_argument("--version", required=True)
    ps.set_defaults(func=cmd_inputs_show)

    p = sub.add_parser("plan", help="预演一次实验（不写文件、不联网）")
    p.add_argument("--input-version", required=True)
    p.add_argument("--task-name", required=True)
    p.add_argument("--mode", choices=["opt", "sampling"], default="opt")
    p.add_argument("--topk", type=int, default=13)
    p.add_argument("--mfactor", type=float, default=1.0)
    p.add_argument("--samples", type=int, default=10)
    p.add_argument("--backend", choices=["real", "mock"], default="real")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("run", help="执行实验（默认 dry-run；--submit 才提交）")
    p.add_argument("--input-version", required=True)
    p.add_argument("--task-name", required=True)
    p.add_argument("--mode", choices=["opt", "sampling"], default="opt")
    p.add_argument("--topk", type=int, default=13)
    p.add_argument("--mfactor", type=float, default=1.0)
    p.add_argument("--samples", type=int, default=10)
    p.add_argument("--submit", action="store_true", help="实际提交（需人工逐字确认）")
    p.add_argument("--backend", choices=["real", "mock"], default="real")
    p.add_argument("--mock-fail-stage", choices=["submit", "run", "download", "interrupt"],
                   default=None, help="仅 mock 后端：注入失败阶段")
    p.add_argument("--allow-matrix-reuse", action="store_true",
                   help="允许同一矩阵换名重复提交（会再消耗配额）")
    p.add_argument("--project-no", default=None)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status", help="查看本地任务状态")
    p.add_argument("--task-id", default=None)
    p.add_argument("--remote", action="store_true", help="额外尝试查询平台状态")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("resume", help="查询并恢复已提交任务的结果（不重新提交）")
    p.add_argument("--task-id", required=True)
    p.add_argument("--local-only", action="store_true", help="只读本地归档，不访问平台")
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("attach-report", help="归档平台导出的原始报告")
    p.add_argument("--task-id", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--device", default=None, help="平台报告中的实际设备型号")
    p.add_argument("--hardware-ms", type=float, default=None, help="平台报告中的硬件求解时间（毫秒）")
    p.add_argument("--platform-task-id", default=None)
    p.set_defaults(func=cmd_attach)

    p = sub.add_parser("budget", help="查看本地配额账本")
    p.set_defaults(func=cmd_budget)

    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.cmd == "inputs":
        return a.func(a)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
