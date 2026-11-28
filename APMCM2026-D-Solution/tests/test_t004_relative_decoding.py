# -*- coding: utf-8 -*-
"""T004-R1：相对自旋解码、Z2 不变性、Top-K 并列边界与量化/采样指标分离。"""
import sys
import unittest
from pathlib import Path

import numpy as np

CODE = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE))

import precision_reducer as PRR          # noqa: E402
import d_submit_cim as S                 # noqa: E402
import d_experiment as DX                # noqa: E402


class RelativeDecodingTest(unittest.TestCase):
    def test_aux_plus_decode(self):
        s = np.array([1, -1, -1, 1], dtype=float)   # A0, B0, aux=+1
        bits = PRR.logical_bits_from_spins(s)[0]
        np.testing.assert_array_equal(bits, [1, 0, 0])

    def test_aux_minus_decode(self):
        s = np.array([-1, 1, 1, -1], dtype=float)   # 全局翻转
        bits = PRR.logical_bits_from_spins(s)[0]
        np.testing.assert_array_equal(bits, [1, 0, 0])

    def test_global_flip_preserves_logical_bits(self):
        rng = np.random.default_rng(0)
        s = rng.choice([-1.0, 1.0], size=(5, 9))
        np.testing.assert_array_equal(
            PRR.logical_bits_from_spins(s), PRR.logical_bits_from_spins(-s))

    def test_global_flip_preserves_hamiltonian(self):
        rng = np.random.default_rng(1)
        J = rng.normal(size=(9, 9))
        J = (J + J.T) / 2
        np.fill_diagonal(J, 0.0)
        s = rng.choice([-1.0, 1.0], size=(5, 9))
        h1 = -np.einsum("ij,ij->i", s @ J, s)
        h2 = -np.einsum("ij,ij->i", (-s) @ J, -s)
        np.testing.assert_allclose(h1, h2, atol=1e-12)

    def test_legal_stays_legal_after_flip(self):
        s = np.array([1, -1, 1, -1, 1], dtype=float)  # A0+B0+aux
        self.assertEqual(PRR.logical_labels_from_spins(s, 2, 2), [(0, 0)])
        self.assertEqual(PRR.logical_labels_from_spins(-s, 2, 2), [(0, 0)])

    def test_illegal_stays_illegal_after_flip(self):
        s = np.array([1, 1, -1, -1, 1], dtype=float)  # 两个 A
        self.assertEqual(PRR.logical_labels_from_spins(s, 2, 2), [None])
        self.assertEqual(PRR.logical_labels_from_spins(-s, 2, 2), [None])

    def test_flipping_aux_alone_changes_logical_state(self):
        s = np.array([1, -1, -1, 1], dtype=float)
        s_aux_flipped = s.copy()
        s_aux_flipped[-1] *= -1
        self.assertFalse(np.array_equal(
            PRR.logical_bits_from_spins(s), PRR.logical_bits_from_spins(s_aux_flipped)))

    def test_precision_reducer_restore_relative_decode(self):
        # 恢复后的原始向量：A0+B0+aux=-1（全局翻转），仍应解码为 (0,0)
        restored = np.array([[-1, 1, -1, 1, -1]], dtype=float)
        V = np.array([[0.0, 10.0], [10.0, 10.0]])
        rows = PRR.evaluate_restored(restored, V, ["A0", "A1"], ["B0", "B1"])
        self.assertTrue(rows[0]["legal"])
        self.assertEqual((rows[0]["A"], rows[0]["B"]), ("A0", "B0"))
        self.assertEqual(rows[0]["V"], 0.0)


class TopKTieBoundaryTest(unittest.TestCase):
    def test_tie_truncation_can_drop_all_raw_optima(self):
        # 每行、每列最小值都是 0，但 topk=1 只取第 0 行/列，交集为 1
        V = np.array([[1.0, 1.0, 0.0],
                      [0.0, 1.0, 1.0],
                      [1.0, 0.0, 1.0]])
        A = ["a0", "a1", "a2"]
        B = ["b0", "b1", "b2"]
        As, Bs, Vs = DX.select_topk(A, B, V, 1)
        self.assertEqual(Vs.min(), 1.0)
        raw = {(A[i], B[j]) for i, j in np.argwhere(V <= 1e-12)}
        kept = {(a, b) for a in As for b in Bs}
        self.assertEqual(len(raw & kept), 0)
        self.assertEqual(raw, {("a0", "b2"), ("a1", "b0"), ("a2", "b1")})


class QuantizedVsSamplingTest(unittest.TestCase):
    def test_sample_can_hit_raw_optimum_outside_quantized_ground_set(self):
        # 量化目标偏爱 (0,1)；原始目标最优是 (0,0)。采样可返回原始最优但非量化基态。
        Vq = np.array([[10.0, 0.0], [10.0, 10.0]])
        Q, off, _ = S.build_qubo(Vq, M=5.0)
        legal = []
        for i in range(2):
            for j in range(2):
                x = np.zeros(4)
                x[i] = 1
                x[2 + j] = 1
                legal.append(((i, j), float(x @ Q @ x + off)))
        hmin = min(v for _, v in legal)
        qset = {lab for lab, v in legal if abs(v - hmin) < 1e-12}
        self.assertEqual(qset, {(0, 1)})

        Vraw = np.array([[0.0, 10.0], [10.0, 10.0]])
        sample = np.array([[1, -1, 1, -1, 1]], dtype=float)  # (0,0)+aux
        rows = PRR.evaluate_restored(sample, Vraw, ["A0", "A1"], ["B0", "B1"])
        self.assertTrue(rows[0]["legal"])
        self.assertEqual((rows[0]["A"], rows[0]["B"]), ("A0", "B0"))
        self.assertNotIn(("A0", "B0"), {(f"A{i}", f"B{j}") for i, j in qset})


if __name__ == "__main__":
    unittest.main()
