# -*- coding: utf-8 -*-
r"""Phase 10 实验基础设施测试（教学矩阵 + 模拟后端，不联网、不耗配额）。

运行：
    & "$env:LOCALAPPDATA\kaiwu-verify\Scripts\python.exe" -m unittest discover -s tests -v
或任意已安装 kaiwu==1.4.4 的 Python 3.12 环境。
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

_SANDBOX = tempfile.mkdtemp(prefix="apmcm_phase10_")
os.environ["APMCM_EXPERIMENT_ROOT"] = _SANDBOX

import d_experiment as dx            # noqa: E402
import experiment_budget as budget   # noqa: E402
import experiment_input as exin      # noqa: E402
import d_submit_cim as S             # noqa: E402
import artifact_consistency as ac    # noqa: E402
from experiment_archive import (  # noqa: E402
    Registry,
    TaskArchive,
    backup_if_exists,
    validate_spin_matrix,
)
from mock_backend import MockCIMOptimizer            # noqa: E402

HAS_KAIWU = importlib.util.find_spec("kaiwu") is not None


def quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(*args, **kwargs), buf.getvalue()


def make_input(version: str, A, B, V, kind: str = "teaching"):
    src = Path(_SANDBOX) / "src" / f"{version}.csv"
    src.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(V, index=A, columns=B).to_csv(src, encoding="utf-8-sig")
    return exin.register(version=version, matrix_path=src, fmt="matrix", kind=kind,
                         sub_question="TEST")


def tearDownModule():
    shutil.rmtree(_SANDBOX, ignore_errors=True)


@unittest.skipUnless(HAS_KAIWU, "需要 kaiwu==1.4.4")
class Phase10Test(unittest.TestCase):
    def setUp(self):
        # 每个用例使用独立版本名，避免互相影响
        self.tag = self._testMethodName

    # ------------------------------------------------------------------ 输入版本
    def test_input_version_isolation_and_tamper_detection(self):
        V1 = np.arange(16, dtype=float).reshape(4, 4)
        V2 = V1 + 100
        make_input("v1_" + self.tag, list("ABCD"), list("WXYZ"), V1)
        make_input("v2_" + self.tag, list("ABCD"), list("WXYZ"), V2)

        e1 = exin.load("v1_" + self.tag)
        e2 = exin.load("v2_" + self.tag)
        self.assertNotEqual(e1.matrix_sha256, e2.matrix_sha256)
        self.assertTrue(np.allclose(e1.V, V1))
        self.assertTrue(np.allclose(e2.V, V2))

        # 篡改已登记版本 → 拒绝加载
        p = e1.dir / "matrix.csv"
        p.write_text("A,W,X,Y,Z\nA,0,0,0,0\n", encoding="utf-8-sig")
        with self.assertRaises(SystemExit):
            exin.load("v1_" + self.tag)

    def test_mixed_kind_refused(self):
        # 声明 official_prediction，但文件路径不像预测目录 → 拒绝
        src = Path(_SANDBOX) / "src" / "plain.csv"
        src.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(np.zeros((3, 3)), index=list("ABC"), columns=list("XYZ")).to_csv(src)
        with self.assertRaises(SystemExit):
            exin.register("mix_" + self.tag, src, fmt="matrix", kind="official_prediction")

    # ------------------------------------------------------------------ dry-run
    def test_dry_run_no_files_no_network(self):
        make_input("dry_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 1, 2], [1, 0, 1], [2, 1, 0]]))
        before = set(Path(exin.tasks_root()).glob("*")) if Path(exin.tasks_root()).exists() else set()

        orig_connect = socket.socket.connect

        def deny(self, *a, **k):
            raise AssertionError("dry-run 不应发起网络连接")

        socket.socket.connect = deny
        try:
            r, out = quiet(dx.execute_task, "dry_" + self.tag, "dry_task", "opt", 0, 1.0, 10,
                           submit=False, backend="mock")
        finally:
            socket.socket.connect = orig_connect

        self.assertEqual(r["status"], "dry_run")
        self.assertFalse(r["submitted"])
        self.assertIn("[DRY-RUN]", out)
        after = set(Path(exin.tasks_root()).glob("*")) if Path(exin.tasks_root()).exists() else set()
        self.assertEqual(before, after, "dry-run 不应创建任务归档")

    # ------------------------------------------------------------------ 配额
    def test_quota_protection_blocks_before_submit(self):
        make_input("quota_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 1, 2], [1, 0, 1], [2, 1, 0]]))
        bp = budget.budget_path()
        original = bp.read_text(encoding="utf-8") if bp.is_file() else None
        data = budget.read_budget()
        data["budgets"]["optimization"]["total"] = 0
        bp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            with self.assertRaises(SystemExit):
                quiet(dx.execute_task, "quota_" + self.tag, "quota_task", "opt", 0, 1.0, 10,
                      submit=True, backend="mock", confirm=True)
        finally:
            if original is None:
                bp.unlink(missing_ok=True)
            else:
                bp.write_text(original, encoding="utf-8")
        self.assertIsNone(Registry().find_duplicate("quota_task", "x" * 64)[0])

    # ------------------------------------------------------------------ 重复拦截
    def test_duplicate_submission_blocked(self):
        make_input("dup_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 1, 2], [1, 0, 1], [2, 0, 0]]))
        r, _ = quiet(dx.execute_task, "dup_" + self.tag, "dup_task", "opt", 0, 1.0, 10,
                     submit=True, backend="mock", confirm=True)
        self.assertEqual(r["status"], "completed")

        with self.assertRaises(SystemExit):
            quiet(dx.execute_task, "dup_" + self.tag, "dup_task", "opt", 0, 1.0, 10,
                  submit=True, backend="mock", confirm=True)

        with self.assertRaises(SystemExit):
            quiet(dx.execute_task, "dup_" + self.tag, "dup_task_2", "opt", 0, 1.0, 10,
                  submit=True, backend="mock", confirm=True)

    # ------------------------------------------------------------------ 归档
    def test_archive_records_raw_and_metadata(self):
        make_input("arc_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 2, 3], [2, 0, 1], [3, 1, 0]]))
        r, _ = quiet(dx.execute_task, "arc_" + self.tag, "arc_task", "opt", 0, 1.0, 10,
                     submit=True, backend="mock", confirm=True)
        self.assertEqual(r["status"], "completed")

        arc = TaskArchive(r["task_id"])
        meta = arc.meta()
        self.assertEqual(meta["status"], "completed")
        self.assertTrue(meta["quota_counted"])
        self.assertTrue(Path(meta["archive_dir"]).is_dir())

        cfg = json.loads((arc.dir / "config.json").read_text(encoding="utf-8"))
        for key in ("input_version", "input_matrix_sha256", "submitted_matrix_sha256",
                    "ising_shape", "git_commit", "sdk_version", "python_version"):
            self.assertIn(key, cfg)

        self.assertTrue((arc.dir / "input" / "matrix.csv").is_file())
        self.assertTrue((arc.dir / "input" / "mapping.json").is_file())
        self.assertTrue((arc.dir / "input" / "ising_matrix.csv").is_file())
        self.assertTrue((arc.dir / "input" / "hashes.json").is_file())
        self.assertTrue((arc.dir / "raw" / "solutions.npz").is_file())
        self.assertTrue((arc.dir / "raw" / "solutions.csv").is_file())
        self.assertTrue((arc.dir / "raw" / "solution_energy.csv").is_file())
        self.assertTrue((arc.dir / "logs" / "run.log").is_file())
        self.assertTrue((arc.dir / "attempts.jsonl").is_file())

        sol = np.load(arc.dir / "raw" / "solutions.npz")["solutions"]
        self.assertEqual(sol.shape, (10, meta["ising_shape"][0]))

        # 凭据类字段不得出现
        blob = (arc.dir / "config.json").read_text(encoding="utf-8").lower()
        for bad in ("sdk_code", "authorization", "user_id", "password", "token"):
            self.assertNotIn(bad, blob)

    # ------------------------------------------------------------------ 失败阶段
    def test_failure_stages_and_resume(self):
        make_input("fail_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 1, 4], [1, 0, 2], [4, 2, 0]]))

        # 提交失败：不计配额
        r, _ = quiet(dx.execute_task, "fail_" + self.tag, "submit_fail", "opt", 0, 1.0, 10,
                     submit=True, backend="mock", mock_fail_stage="submit", confirm=True)
        self.assertEqual(r["status"], "submit_failed")
        self.assertFalse(TaskArchive(r["task_id"]).meta()["quota_counted"])

        # 运行失败（同一矩阵故意重跑，验证失败阶段判定）
        r, _ = quiet(dx.execute_task, "fail_" + self.tag, "run_fail", "opt", 0, 1.0, 10,
                     submit=True, backend="mock", mock_fail_stage="run", confirm=True,
                     allow_matrix_reuse=True)
        self.assertEqual(r["status"], "run_failed")
        self.assertTrue(TaskArchive(r["task_id"]).meta()["quota_counted"])

        # 下载失败 → 恢复成功，且不重新提交
        r, _ = quiet(dx.execute_task, "fail_" + self.tag, "download_fail", "opt", 0, 1.0, 10,
                     submit=True, backend="mock", mock_fail_stage="download", confirm=True,
                     allow_matrix_reuse=True)
        self.assertEqual(r["status"], "download_failed")
        tid = r["task_id"]

        fake = MockCIMOptimizer("download_fail", sample_number=10)
        fake.submitted = True  # 模拟云端已有任务
        rr, out = quiet(dx.resume_task, tid, fake)
        self.assertEqual(rr["status"], "completed")
        self.assertEqual(fake.submit_count, 0, "恢复不得重新提交")
        self.assertTrue((TaskArchive(tid).dir / "raw" / "platform_result.json").is_file())

    # ------------------------------------------------------------------ 归档只读
    def test_archive_never_overwritten(self):
        make_input("ro_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 1, 2], [1, 0, 3], [2, 3, 0]]))
        r, _ = quiet(dx.execute_task, "ro_" + self.tag, "ro_task", "opt", 0, 1.0, 10,
                     submit=True, backend="mock", confirm=True)
        arc = TaskArchive(r["task_id"])
        with self.assertRaises(SystemExit):
            arc.save_solutions(np.ones((2, 3), dtype=int))

    # ------------------------------------------------------------------ 报告归档
    def test_attach_platform_report(self):
        make_input("rep_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 1, 2], [1, 0, 4], [2, 4, 0]]))
        r, _ = quiet(dx.execute_task, "rep_" + self.tag, "rep_task", "opt", 0, 1.0, 10,
                     submit=True, backend="mock", confirm=True)
        pdf = Path(_SANDBOX) / "vendor_report.pdf"
        pdf.write_bytes(b"%PDF-1.4 mock report\n")
        arc = TaskArchive(r["task_id"])
        meta = arc.attach_report(pdf, device="SPQC-550", platform_task_id="mock-task-id")
        self.assertEqual(meta["device"], "SPQC-550")
        self.assertEqual(meta["device_source"], "platform_report")
        self.assertTrue((arc.dir / "reports" / "vendor_report.pdf").is_file())


    # ------------------------------------------------------------------ 修复回归
    def test_unknown_failure_is_conservative(self):
        """未预期异常不得当成“未提交”，必须计配额并拦截重复提交。"""
        make_input("unk_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 1, 5], [1, 0, 2], [5, 2, 0]]))
        r, _ = quiet(dx.execute_task, "unk_" + self.tag, "unknown_task", "opt", 0, 1.0, 10,
                     submit=True, backend="mock", mock_fail_stage="unknown", confirm=True)
        self.assertEqual(r["status"], "unknown_failure")
        self.assertTrue(TaskArchive(r["task_id"]).meta()["quota_counted"])

        with self.assertRaises(SystemExit):
            quiet(dx.execute_task, "unk_" + self.tag, "unknown_task", "opt", 0, 1.0, 10,
                  submit=True, backend="mock", confirm=True)

    def test_backend_prepare_failure_is_retryable(self):
        """授权/构造失败发生在提交前，应记为 submit_failed 且允许同名重试。"""
        make_input("prep_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 2, 6], [2, 0, 1], [6, 1, 0]]))
        with mock.patch.object(dx, "_prepare_backend", side_effect=ValueError("license missing")):
            r, _ = quiet(dx.execute_task, "prep_" + self.tag, "prep_task", "opt", 0, 1.0, 10,
                         submit=True, backend="real", confirm=True)
        self.assertEqual(r["status"], "submit_failed")
        self.assertFalse(TaskArchive(r["task_id"]).meta()["quota_counted"])

        r2, _ = quiet(dx.execute_task, "prep_" + self.tag, "prep_task", "opt", 0, 1.0, 10,
                      submit=True, backend="mock", confirm=True)
        self.assertEqual(r2["status"], "completed")

    def test_invalid_solution_shape_rejected(self):
        """返回解列数或取值非法时，原样归档但不得标记为 completed。"""
        make_input("bad_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 1, 7], [1, 0, 3], [7, 3, 0]]))

        class BadMock(MockCIMOptimizer):
            def _solutions(self, matrix):
                arr = super()._solutions(matrix)
                arr[0, 0] = 0
                return arr

        with mock.patch("mock_backend.MockCIMOptimizer", BadMock):
            r, _ = quiet(dx.execute_task, "bad_" + self.tag, "bad_task", "opt", 0, 1.0, 10,
                         submit=True, backend="mock", confirm=True)
        self.assertEqual(r["status"], "invalid_result")
        arc = TaskArchive(r["task_id"])
        self.assertTrue(arc.meta()["quota_counted"])
        self.assertTrue((arc.dir / "raw" / "solutions.npz").is_file())

    def test_run_arg_validation(self):
        make_input("args_" + self.tag, list("ABC"), list("XYZ"),
                   np.array([[0.0, 1, 2], [1, 0, 3], [2, 3, 0]]))
        with self.assertRaises(SystemExit):
            quiet(dx.execute_task, "args_" + self.tag, "bad_topk", "opt", -1, 1.0, 10,
                  submit=False, backend="mock")
        with self.assertRaises(SystemExit):
            quiet(dx.execute_task, "args_" + self.tag, "bad_samples", "opt", 0, 1.0, 5,
                  submit=False, backend="mock")
        with self.assertRaises(SystemExit):
            quiet(dx.execute_task, "args_" + self.tag, "bad_samples", "opt", 0, 1.0, 5000,
                  submit=False, backend="mock")

    def test_validate_spin_matrix(self):
        good = np.array([[1, -1, 1], [-1, 1, -1]])
        self.assertEqual(validate_spin_matrix(good, 3).shape, (2, 3))
        with self.assertRaises(ValueError):
            validate_spin_matrix(good, 4)
        bad = good.copy()
        bad[0, 0] = 0
        with self.assertRaises(ValueError):
            validate_spin_matrix(bad, 3)
        with self.assertRaises(ValueError):
            validate_spin_matrix(np.empty((0, 3)), 3)

    def test_backup_if_exists_preserves_old_output(self):
        p = Path(_SANDBOX) / f"old_{self.tag}.csv"
        p.write_text("old-content", encoding="utf-8")
        backup = backup_if_exists(p)
        self.assertIsNotNone(backup)
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_text(encoding="utf-8"), "old-content")
        self.assertTrue(p.is_file())
        self.assertIsNone(backup_if_exists(Path(_SANDBOX) / f"missing_{self.tag}.csv"))

    def test_dry_run_separates_requested_and_returned_samples(self):
        import d_run_stats
        stats, _ = quiet(d_run_stats.run, "dry_stats_" + self.tag, 13, 1.0, "opt", 200,
                         submit=False)
        self.assertEqual(stats["sample_number_param"], 200)
        self.assertIsNone(stats["samples"])
        self.assertIsNone(stats["returned_solutions"])
        self.assertFalse(stats["submitted"])


    def test_load_pool_refuses_duplicate_ab_without_x(self):
        pool_dir = Path(_SANDBOX) / "pools"
        pool_dir.mkdir(parents=True, exist_ok=True)
        p = pool_dir / "dup_pool.csv"
        pd.DataFrame([
            dict(A="La", B="Hf", X="NO2", V_hat=0.0),
            dict(A="La", B="Hf", X="O3", V_hat=5.0),
            dict(A="La", B="Zr", X="NO2", V_hat=0.1),
        ]).to_csv(p, index=False)
        with mock.patch.object(S, "PRED", pool_dir):
            with self.assertRaises(SystemExit):
                S.load_pool("dup_pool.csv")
            A, B, V = S.load_pool("dup_pool.csv", x_value="NO2")
        self.assertEqual(A, ["La"])
        self.assertEqual(B, ["Hf", "Zr"])
        self.assertEqual(V.shape, (1, 2))

    def test_q3_long_input_requires_explicit_x(self):
        p = Path(_SANDBOX) / f"q3_long_{self.tag}.csv"
        pd.DataFrame([
            dict(A="Pb", B="Ti", X="O3", V_hat=0.0),
            dict(A="Pb", B="Sc", X="O3", V_hat=0.4),
            dict(A="Ba", B="Ti", X="O3", V_hat=0.5),
            dict(A="Ba", B="Sc", X="O3", V_hat=0.0),
            dict(A="Pb", B="Ti", X="NO2", V_hat=6.4),
        ]).to_csv(p, index=False)
        with self.assertRaises(SystemExit):
            exin.register(f"q3_no_x_{self.tag}", p, fmt="long", kind="teaching",
                          sub_question="Q3")
        vdir = exin.register(f"q3_with_x_{self.tag}", p, fmt="long", kind="teaching",
                             sub_question="Q3", x_col="X", x_value="O3")
        manifest = json.loads((vdir / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["x_declared"])
        self.assertEqual(manifest["x_value"], "O3")
        self.assertEqual(manifest["shape"], [2, 2])

    def test_artifact_diff_stats(self):
        self.assertEqual(ac.diff_stats([1, 2], [1, 2])["status"], "OK")
        bad = ac.diff_stats([1, 2], [1, 3])
        self.assertEqual(bad["status"], "MISMATCH")
        self.assertEqual(bad["max_abs"], 1.0)
        shape = ac.diff_stats([1, 2], [1, 2, 3])
        self.assertEqual(shape["status"], "SHAPE_MISMATCH")

    def test_h_direction_and_dual_resolution_recorded(self):
        import d_run_stats
        stats, _ = quiet(d_run_stats.run, "hdir_" + self.tag, 13, 1.0, "opt", 10,
                         submit=False)
        self.assertEqual(stats["h_direction"], "lower_is_better")
        self.assertIn("resol_raw", stats)
        self.assertIn("resol_adj", stats)
        self.assertNotAlmostEqual(stats["resol_raw"], stats["resol_adj"], places=3)

        text = (CODE / "d_run_stats.py").read_text(encoding="utf-8")
        self.assertIn('ascending=True', text)
        self.assertIn("越小越好", text)
        self.assertNotIn('ascending=False', text)
        self.assertNotIn("越大越好", text)

    def test_no_physical_optimum_claim_in_code(self):
        for name in ("d_submit_cim.py", "d_run_stats.py", "run_all.py"):
            text = (CODE / name).read_text(encoding="utf-8")
            self.assertNotIn("穷举金标准", text, name)
            self.assertNotIn("真值最优", text, name)
        self.assertIn("代理模型矩阵", (CODE / "d_submit_cim.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
