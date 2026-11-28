# -*- coding: utf-8 -*-
"""resume 不得把已 completed 的任务降级；不联网、不消耗配额。"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import d_experiment as dx            # noqa: E402
import experiment_input as exin      # noqa: E402
from experiment_archive import Registry, TaskArchive  # noqa: E402


class _FailingBackend:
    def get_task_result(self, matrix):
        raise RuntimeError("mock platform unavailable")


class _EmptyBackend:
    def get_task_result(self, matrix):
        return {"status": "not_found", "task_status_code": "UNKNOWN"}


class ResumeGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("APMCM_EXPERIMENT_ROOT")
        os.environ["APMCM_EXPERIMENT_ROOT"] = self.tmp.name
        inputs = Path(self.tmp.name) / "inputs"
        inputs.mkdir(parents=True)
        shutil.copytree(ROOT / "experiments" / "inputs" / "B-Q2-NO2",
                        inputs / "B-Q2-NO2")
        self.exin = exin.load("B-Q2-NO2")
        p = dx.build_problem(self.exin, topk=2, mfactor=1.0)
        self.tid = "t_resume_guard"
        arc = TaskArchive.create(self.tid, {"task_name": "t", "mode": "opt",
                                            "mode_key": "optimization",
                                            "topk": 2, "mfactor": 1.0,
                                            "samples": 10, "quota_units": 1},
                                 self.exin, p["adj"], raw_ising_matrix=p["I"],
                                 submitted_A=p["A"], submitted_B=p["B"],
                                 filtered_V=p["V"])
        sol = np.ones((1, p["n_ising"]))
        arc.save_solutions(sol)
        arc.save_energy(sol, p["adj"])
        arc.update(status="completed", quota_counted=True)
        Registry().add({"task_id": self.tid, "task_name": "t",
                        "status": "completed", "mode_key": "optimization",
                        "quota_units": 1, "quota_counted": True})

    def tearDown(self):
        if self.old is None:
            os.environ.pop("APMCM_EXPERIMENT_ROOT", None)
        else:
            os.environ["APMCM_EXPERIMENT_ROOT"] = self.old
        self.tmp.cleanup()

    def _assert_completed(self):
        arc = TaskArchive(self.tid)
        self.assertEqual(arc.meta()["status"], "completed")
        reg = Registry()
        entry = next(t for t in reg.tasks if t["task_id"] == self.tid)
        self.assertEqual(entry["status"], "completed")

    def test_query_failure_does_not_downgrade_completed(self):
        r = dx.resume_task(self.tid, backend=_FailingBackend())
        self.assertEqual(r["status"], "completed")
        self.assertIn("local completed preserved", r["note"])
        self._assert_completed()

    def test_empty_result_does_not_downgrade_completed(self):
        r = dx.resume_task(self.tid, backend=_EmptyBackend())
        self.assertEqual(r["status"], "completed")
        self.assertIn("local completed preserved", r["note"])
        self._assert_completed()


if __name__ == "__main__":
    unittest.main()
