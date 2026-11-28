# -*- coding: utf-8 -*-
"""T003：PrecisionReducer 路线的回归测试（本地，不联网、不消耗配额）。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

CODE = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE))

import d_experiment as dx            # noqa: E402
import experiment_input as exin      # noqa: E402
import kaiwu.preprocess as pp        # noqa: E402
import precision_reducer as PRR      # noqa: E402
from experiment_archive import TaskArchive  # noqa: E402

LOWM = 0.33826009024559534
TP12 = {"precision": 8, "target_bits": 550,
        "truncated_precision": 12, "only_feasible_solution": False}


class PrecisionReducerRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        cls._old_env = os.environ.get("APMCM_EXPERIMENT_ROOT")
        os.environ["APMCM_EXPERIMENT_ROOT"] = str(
            Path(__file__).resolve().parents[1] / "experiments")
        cls.exin = exin.load("B-Q2-NO2")

    @classmethod
    def tearDownClass(cls):
        import os
        if cls._old_env is None:
            os.environ.pop("APMCM_EXPERIMENT_ROOT", None)
        else:
            os.environ["APMCM_EXPERIMENT_ROOT"] = cls._old_env

    def test_direct8_route_hash_unchanged(self):
        p = dx.build_problem(self.exin, topk=8, mfactor=LOWM)
        self.assertEqual(
            p["matrix_sha256"],
            "34f84ed6633373975e3211b6099b20313a26d3734fa3770dded0187767454b30")
        self.assertEqual(p["n_ising"], 17)
        self.assertEqual(p["split_extra_spins"], 0)

    def test_precision_reducer_expansion_and_mapping(self):
        p = dx.build_problem(self.exin, topk=8, mfactor=LOWM,
                             precision_method="precision_reducer", pr_params=TP12)
        self.assertEqual(p["n_ising_original"], 17)
        self.assertEqual(p["n_ising"], 62)
        self.assertEqual(p["split_extra_spins"], 45)
        self.assertEqual(p["mapping_status"], "verified_reconstruction")
        self.assertEqual(len(p["split_groups"]), 17)
        self.assertTrue(p["submitted_equals_expanded"])
        self.assertLessEqual(pp.calculate_ising_matrix_bit_width(p["adj"], 8)["precision"], 8)
        variables = PRR.expanded_variables(p["A"], p["B"], p["n_ising_original"],
                                           p["split_indices"])
        self.assertEqual(len(variables), p["n_ising"])
        self.assertEqual(variables[-1]["index"], p["n_ising"] - 1)
        self.assertEqual(variables[-1]["kind"], "aux")

    def test_constructed_optimum_is_split_feasible_and_restores(self):
        p = dx.build_problem(self.exin, topk=8, mfactor=LOWM,
                             precision_method="precision_reducer", pr_params=TP12)
        V = p["V"]
        i, j = np.unravel_index(np.argmin(V), V.shape)
        s = np.full(p["n_ising_original"], -1.0)
        s[i] = 1.0
        s[V.shape[0] + j] = 1.0
        s[-1] = 1.0
        exp = np.asarray(pp.construct_split_solution(s, p["split_indices"]), float)
        self.assertTrue(bool(PRR.split_feasible(np.atleast_2d(exp), p["split_groups"])[0]))
        back = pp.restore_split_solution(exp, p["split_indices"])
        self.assertTrue(np.array_equal(np.asarray(back), s))

    def test_archive_with_precision_meta(self):
        p = dx.build_problem(self.exin, topk=8, mfactor=LOWM,
                             precision_method="precision_reducer", pr_params=TP12)
        meta = PRR.split_mapping_payload({
            "params": p["precision_params"], "n_original": p["n_ising_original"],
            "n_expanded": p["n_ising"], "n_extra": p["split_extra_spins"],
            "mapping_status": p["mapping_status"], "mapping_evidence": p["mapping_evidence"],
            "split_indices": p["split_indices"], "bit_width": p["submitted_bit_width"],
            "submitted_multiplier": p["submitted_bit_width"].get("multiplier"),
            "submitted_equals_expanded": p["submitted_equals_expanded"],
        }, p["A"], p["B"])
        with tempfile.TemporaryDirectory() as tmp:
            arc = TaskArchive.create(
                "t_test_pr", {"task_name": "t", "topk": 8, "mfactor": LOWM},
                self.exin, p["adj"], raw_ising_matrix=p["I"],
                submitted_A=p["A"], submitted_B=p["B"], filtered_V=p["V"],
                precision_meta=meta, expanded_matrix=p["expanded_matrix"],
                root=Path(tmp))
            for name in ("input/split_mapping.json", "input/ising_matrix_expanded.npz",
                         "input/ising_matrix_raw.npz", "input/submitted_mapping.json"):
                self.assertTrue((arc.dir / name).is_file(), name)
            sm = json.loads((arc.dir / "input/split_mapping.json").read_text(encoding="utf-8"))
            self.assertEqual(sm["n_expanded"], 62)
            self.assertEqual(len(sm["variables"]), 62)
            mp = json.loads((arc.dir / "input/submitted_mapping.json").read_text(encoding="utf-8"))
            self.assertEqual(mp["n_ising"], 62)
            self.assertEqual(mp["n_ising_original"], 17)
            self.assertEqual(mp["split_extra_spins"], 45)


if __name__ == "__main__":
    unittest.main()
