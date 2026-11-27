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
from experiment_archive import Registry, TaskArchive  # noqa: E402
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
