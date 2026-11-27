"""通用 QUBO/Ising 接口验证：只用非赛题教学矩阵与小规模枚举。

不修改任何正式模型、参数或结论；目的只是把数学接口的事实固定成可回归测试。
"""
import itertools
import sys
import unittest
from pathlib import Path

import numpy as np

CODE = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE))

import kaiwu.preprocess as pp  # noqa: E402
import d_submit_cim as S  # noqa: E402


def _states(n):
    return [np.array(s, dtype=float) for s in itertools.product([-1, 1], repeat=n)]


class MathInterfaceTest(unittest.TestCase):
    def test_qubo_ising_identity_only_in_aux_plus_gauge(self):
        V = np.array([[0.0, 1.0, 5.0], [2.0, 0.0, 4.0], [3.0, 3.0, 0.0]])
        Q, _, _ = S.build_qubo(V, M=25.0)
        I, bias = S.to_ising(Q)
        self.assertTrue(np.allclose(I, I.T))
        self.assertEqual(float(np.abs(np.diag(I)).max()), 0.0)
        plus_bad = minus_bad = 0.0
        for bits in itertools.product([0, 1], repeat=Q.shape[0]):
            x = np.array(bits, dtype=float)
            qv = float(x @ Q @ x)
            for aux in (-1.0, 1.0):
                s = np.concatenate([2 * x - 1, [aux]])
                dev = abs(qv - float(-s @ I @ s) - bias)
                if aux == 1.0:
                    plus_bad = max(plus_bad, dev)
                else:
                    minus_bad = max(minus_bad, dev)
        self.assertLess(plus_bad, 1e-9)
        self.assertGreater(minus_bad, 1e-6)

    def test_onehot_penalty_and_aux_degeneracy(self):
        V = np.array([[0.0, 3.0], [4.0, 0.0]])
        A, B = ["a1", "a2"], ["b1", "b2"]
        Q, _, M = S.build_qubo(V)
        I, _ = S.to_ising(Q)
        rows = []
        for s in _states(I.shape[0]):
            H = float(-s @ I @ s)
            bits = ((s + 1) / 2).astype(int)
            valid = bits[:2].sum() == 1 and bits[2:4].sum() == 1
            rows.append((H, valid, tuple(bits[:4])))
        best_valid = min(r[0] for r in rows if r[1])
        best_invalid = min(r[0] for r in rows if not r[1])
        self.assertLess(best_valid, best_invalid)
        self.assertAlmostEqual(best_invalid - best_valid, M, places=6)

        # 合法 one-hot 解的线性场为零，aux=+1/-1 的 H 相同
        x = np.array([1, 0, 1, 0])
        hs = []
        for aux in (-1.0, 1.0):
            s = np.concatenate([2 * x - 1, [aux]])
            hs.append(float(-s @ I @ s))
        self.assertAlmostEqual(hs[0], hs[1], places=9)

        self.assertIsNone(S.decode(np.array([1, 1, 0, 0]), A, B))
        self.assertEqual(S.decode(np.array([1, 0, 0, 1]), A, B), ("a1", "b2"))

    def test_spin_flip_delta_h_is_twice_the_code_formula(self):
        rng = np.random.default_rng(20261127)
        J = rng.normal(size=(4, 4)); J = (J + J.T) / 2
        states = _states(4)
        H = {tuple(s.astype(int)): float(-s @ J @ s) for s in states}
        for s in states:
            for i in range(4):
                sn = s.copy(); sn[i] = -sn[i]
                exact = H[tuple(sn.astype(int))] - H[tuple(s.astype(int))]
                code = 2 * s[i] * (J[i] @ s) - 2 * J[i, i]
                exact_formula = 4 * s[i] * (J[i] @ s) - 4 * J[i, i]
                self.assertAlmostEqual(code, exact / 2, places=9)
                self.assertAlmostEqual(exact_formula, exact, places=9)

    def test_quantization_can_change_legal_argmin(self):
        # 教学矩阵：原始最优 (2,0)，8bit 适配后最优 (1,0)，两者不相交
        V = np.array([
            [0.2544058321170608, 1.478493748067384, 0.3913056598906419],
            [0.12384047029690515, 1.1967842146480763, 1.7915155034825632],
            [0.053886822769405596, 1.6102719797833385, 0.38034003345668155],
        ])
        Q, _, _ = S.build_qubo(V)
        I, _ = S.to_ising(Q)
        adj = np.asarray(pp.adjust_ising_matrix_precision(I, 8), dtype=float)
        rows = []
        for i in range(3):
            for j in range(3):
                s = np.zeros(7); s[i] = 1; s[3 + j] = 1; s[-1] = 1; s = 2 * s - 1
                rows.append((i, j, float(-s @ I @ s), float(-s @ adj @ s)))
        raw_min = min(r[2] for r in rows)
        adj_min = min(r[3] for r in rows)
        raw_set = {(r[0], r[1]) for r in rows if abs(r[2] - raw_min) < 1e-9}
        adj_set = {(r[0], r[1]) for r in rows if abs(r[3] - adj_min) < 1e-9}
        self.assertEqual(raw_set, {(2, 0)})
        self.assertEqual(adj_set, {(1, 0)})

    def test_full_space_optimum_is_not_legal_optimum_without_penalty(self):
        V = np.array([[0.5, 0.7], [0.9, 0.6]])
        Q = np.zeros((4, 4)); Q[:2, 2:] = V
        I, _ = S.to_ising(Q)
        legal, full = [], []
        for s in _states(I.shape[0]):
            H = float(-s @ I @ s)
            bits = ((s + 1) / 2).astype(int)[:4]
            legal_ok = bits[:2].sum() == 1 and bits[2:].sum() == 1
            full.append((H, legal_ok, tuple(bits)))
            if legal_ok:
                legal.append(H)
        full_min = min(x[0] for x in full)
        legal_min = min(legal)
        self.assertLess(full_min, legal_min)  # 空集/多重选择可能更低
        self.assertFalse(min(full)[1])

        # 加上 one-hot 罚项后，合法解重新成为全空间最优
        Qp, _, _ = S.build_qubo(V)
        Ip, _ = S.to_ising(Qp)
        best = min((float(-s @ Ip @ s), tuple(((s + 1) / 2).astype(int)[:4]))
                   for s in _states(Ip.shape[0]))
        bits = np.array(best[1])
        self.assertEqual(bits[:2].sum(), 1)
        self.assertEqual(bits[2:].sum(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
