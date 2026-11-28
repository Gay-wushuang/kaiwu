# -*- coding: utf-8 -*-
"""PrecisionReducer 旁路验证：真实 SDK + 小规模确定性穷举，不联网、不需要 license。"""
import contextlib
import importlib.util
import io
import itertools
import json
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

CODE = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE))
HAS_KAIWU = importlib.util.find_spec("kaiwu") is not None

if HAS_KAIWU:
    import kaiwu.preprocess as pp
    import d_precision_reducer as pr


@unittest.skipUnless(HAS_KAIWU, "需要 kaiwu==1.4.4")
class PrecisionReducerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = pr.build_ising(pr.TEACHING_V)
        cls.I = cls.model["I"]
        cls.states = np.asarray(list(itertools.product(
            [-1, 1], repeat=cls.I.shape[0])), dtype=np.int8)
        cls.transform = pr.reducer_adapt(cls.I)

    def test_direct_baseline_is_unchanged(self):
        expected = np.asarray(pp.adjust_ising_matrix_precision(self.I, 8), dtype=float)
        actual = pr.direct_adapt(self.I)
        self.assertTrue(np.array_equal(actual, expected))
        self.assertEqual(actual.shape, self.I.shape)
        self.assertLessEqual(pr.bit_width_info(actual)["precision"], 8)

    def test_split_restore_roundtrip_for_full_teaching_space(self):
        representatives = self.transform["representatives"]
        self.assertEqual(representatives.shape, (self.I.shape[0],))
        for state in self.states:
            split = pp.construct_split_solution(state, representatives)
            restored = pp.restore_split_solution(split, representatives)
            self.assertTrue(np.array_equal(restored, state))

    def test_reducer_restores_full_space_and_uses_replayed_matrix(self):
        recovery = pr.verify_reducer_recovery(self.I, self.states, self.transform)
        self.assertTrue(recovery["roundtrip_exact"])
        self.assertEqual(recovery["returned_shape"], list(self.states.shape))
        self.assertEqual(recovery["actual_split_shape"], list(self.transform["matrix"].shape))
        self.assertEqual(recovery["aux_gauge_values"], [1])

    def test_teaching_fidelity_direct_flips_but_reducer_retains_optimum(self):
        raw_states = pr.legal_states(len(pr.TEACHING_A), len(pr.TEACHING_B))
        direct = pr.direct_adapt(self.I)
        direct_metrics = pr.fidelity_metrics(
            self.I, direct, raw_states, raw_states,
            pr.TEACHING_A, pr.TEACHING_B, pr.TEACHING_V)
        reducer_states = pr._adapted_states(raw_states, self.transform["representatives"])
        reducer_metrics = pr.fidelity_metrics(
            self.I, self.transform["matrix"], raw_states, reducer_states,
            pr.TEACHING_A, pr.TEACHING_B, pr.TEACHING_V)
        self.assertFalse(direct_metrics["raw_optimum_retained"])
        self.assertEqual(direct_metrics["best_pair"], ["a2", "b1"])
        self.assertTrue(reducer_metrics["raw_optimum_retained"])
        self.assertEqual(reducer_metrics["best_pair"], ["a3", "b1"])
        self.assertEqual(reducer_metrics["pairwise_agreement"], 1.0)
        self.assertGreater(reducer_metrics["pairwise_agreement"],
                           direct_metrics["pairwise_agreement"])

    def test_comparison_reports_mutation_without_assuming_improvement(self):
        result = pr.run_comparison(
            pr.TEACHING_A, pr.TEACHING_B, pr.TEACHING_V,
            mutate_iterations=3, seed=7)
        self.assertTrue(result["mutation"]["enabled"])
        self.assertIn("dynamic_range_before", result["mutation"])
        self.assertIn("dynamic_range_after", result["mutation"])
        self.assertIn("mutate_then_direct", result["strategies"])
        self.assertGreaterEqual(result["mutation"]["adaptation_ms"], 0)
        # mutate 不保证改善；只要求结果被如实记录且 JSON 可序列化。
        json.dumps(result, allow_nan=False)

    def test_demo_cli_is_offline_and_emits_strict_json(self):
        output = io.StringIO()
        with mock.patch.object(socket.socket, "connect",
                               side_effect=AssertionError("离线测试不应联网")):
            with contextlib.redirect_stdout(output):
                code = pr.main(["--demo", "--mutate-iterations", "0", "--seed", "7"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["input"]["kind"], "teaching")
        self.assertTrue(payload["reducer"]["recovery"]["roundtrip_exact"])
        # aux=±1 规范化为 +1 后，每个合法 one-hot 指派各出现两次。
        self.assertEqual(payload["reducer"]["recovery"]["legal_candidate_count"], 18)
        self.assertEqual(payload["reducer"]["recovery"]["legal_candidate_rate"], 18 / 128)
        self.assertIn("no network", payload["scope"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
