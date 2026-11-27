# -*- coding: utf-8 -*-
"""T002-A 教学例子独立复算：只验证数学命题与数字，不依赖正式赛题数据。"""
import itertools
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
checks = []


def check(name, ok, detail):
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    if not ok:
        print(f"[FAIL] {name}: {detail}")


def example_penalty():
    rows = {}
    for x, y in itertools.product([0, 1], repeat=2):
        f = 3 * x - 2 * y - 7 * x * y
        p = y * (1 + x)
        rows[(x, y)] = (f, p)
    legal = [v[0] for (x, y), v in rows.items() if y == 0]
    a, b = min(legal), max(legal)
    illegal = [(v[0], v[1]) for (x, y), v in rows.items() if y == 1]
    T_a = max((a - f) / p for f, p in illegal)
    T_b = max((b - f) / p for f, p in illegal)
    check("罚项例 T(a)=3", abs(T_a - 3) < 1e-12, f"T(a)={T_a}, rows={rows}")
    check("罚项例 T(b)=5", abs(T_b - 5) < 1e-12, f"T(b)={T_b}")
    M = 3
    h = {k: f + M * p for k, (f, p) in rows.items()}
    check("M=3 时 00 与 11 并列", abs(h[(0, 0)] - h[(1, 1)]) < 1e-12,
          f"H={h}")
    M = 4
    h = {k: f + M * p for k, (f, p) in rows.items()}
    check("M=4 时 00 唯一最优", min(h, key=h.get) == (0, 0), f"H={h}")
    check("M=4 时非法 01/11 优于合法 10",
          min(h[(0, 1)], h[(1, 1)]) < h[(1, 0)], f"H={h}")
    M = 5
    h = {k: f + M * p for k, (f, p) in rows.items()}
    check("M=5 时 01 与 10 并列", abs(h[(0, 1)] - h[(1, 0)]) < 1e-12, f"H={h}")


def example_encodings():
    for z in (0, 1):
        onehot = {}
        for e in itertools.product([0, 1], repeat=4):
            val = e[0] + 3 * e[1] + 2 * e[2] + (5 + 2 * z) * e[3] + 8 * (sum(e) - 1) ** 2
            onehot[e] = val
        valid = [v for e, v in onehot.items() if sum(e) == 1]
        invalid = [v for e, v in onehot.items() if sum(e) != 1]
        check(f"one-hot z={z} 合法成本", sorted(valid) == sorted([1, 3, 2, 5 + 2 * z]),
              str(valid))
        check(f"one-hot z={z} 最低非法=8", min(invalid) == 8, str(min(invalid)))

        dw = {}
        for t in itertools.product([0, 1], repeat=3):
            val = 1 + 2 * t[0] - t[1] + (3 + 2 * z) * t[2] + \
                  8 * ((1 - t[0]) * t[1] + (1 - t[1]) * t[2])
            dw[t] = val
        valid_codes = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1)]
        check(f"domain-wall z={z} 合法成本",
              [dw[t] for t in valid_codes] == [1, 3, 2, 5 + 2 * z],
              str([dw[t] for t in valid_codes]))
        check(f"domain-wall z={z} 最低非法=8",
              min(v for t, v in dw.items() if t not in valid_codes) == 8,
              str(sorted((v, t) for t, v in dw.items() if t not in valid_codes)[:3]))

        binary = {}
        for a, b, w in itertools.product([0, 1], repeat=3):
            val = 1 + 2 * a + b + w + 2 * z * w + \
                  8 * (a * b - 2 * a * w - 2 * b * w + 3 * w)
            binary[(a, b, w)] = val
        valid_b = [v for (a, b, w), v in binary.items() if w == a * b]
        invalid_b = [v for (a, b, w), v in binary.items() if w != a * b]
        check(f"binary z={z} 合法成本",
              sorted(valid_b) == [1, 2, 3, 5 + 2 * z], str(sorted(valid_b)))
        check(f"binary z={z} 最低辅助不一致={11 + z}",
              min(invalid_b) == 11 + z, str(min(invalid_b)))

    # domain-wall/one-hot 双射证据（d=4）
    e = {(0, 0, 0): (1, 0, 0, 0), (1, 0, 0): (0, 1, 0, 0),
         (1, 1, 0): (0, 0, 1, 0), (1, 1, 1): (0, 0, 0, 1)}
    ok = all(sum(v) == 1 and
             all(v[r] == (1 if r == 0 else t[r - 1]) - (t[r] if r < 3 else 0)
                 for r in range(4))
             for t, v in e.items())
    check("domain-wall 到 one-hot 的 e_r=t_r-t_{r+1} 映射", ok, str(e))


def example_quantization():
    A = (-1, +1, +1)
    B = (+1, -1, +1)

    def h(s, coef):
        return coef[0] * s[0] + coef[1] * s[0] * s[2] + coef[2] * s[1]

    real = (0.49, 0.49, 0.80)
    check("量化例实数 H(B)-H(A)=0.36",
          abs(h(B, real) - h(A, real) - 0.36) < 1e-12,
          f"H(A)={h(A, real)}, H(B)={h(B, real)}")
    expected = {0.5: (0, 0, 0, 0), 1.0: (0, 0, 1, -2),
                1.25: (1, 1, 1, 2), 2.0: (1, 1, 2, 0)}
    for alpha, (c1, c13, c2, diff) in expected.items():
        coef = (round(real[0] * alpha), round(real[1] * alpha), round(real[2] * alpha))
        got = h(B, coef) - h(A, coef)
        check(f"量化例 alpha={alpha} 整数系数", coef == (c1, c13, c2), str(coef))
        check(f"量化例 alpha={alpha} 能差", got == diff, f"got={got}, expected={diff}")
    check("量化例第一分界 0.5/0.80", abs(0.5 / 0.80 - 0.625) < 1e-12, "0.625")
    check("量化例第二分界 0.5/0.49", abs(0.5 / 0.49 - 50 / 49) < 1e-12, "50/49")


def example_affine_counterexample():
    def H(x, y):
        return x + 2 * y + 0.75 * (x + y - 1) ** 2

    def K(x, y):
        return H(x, y) - (x + y)

    legal_h = {(1, 0): H(1, 0), (0, 1): H(0, 1)}
    legal_k = {(1, 0): K(1, 0), (0, 1): K(0, 1)}
    check("仿射例合法域排序保持",
          (legal_h[(1, 0)] < legal_h[(0, 1)]) == (legal_k[(1, 0)] < legal_k[(0, 1)]),
          f"H={legal_h}, K={legal_k}")
    full_h = {(x, y): H(x, y) for x, y in itertools.product([0, 1], repeat=2)}
    full_k = {(x, y): K(x, y) for x, y in itertools.product([0, 1], repeat=2)}
    check("仿射例全空间 H 最优=00", min(full_h, key=full_h.get) == (0, 0), str(full_h))
    check("仿射例全空间 K 最优=10", min(full_k, key=full_k.get) == (1, 0), str(full_k))


def main():
    example_penalty()
    example_encodings()
    example_quantization()
    example_affine_counterexample()
    summary = {"pass": sum(c["status"] == "PASS" for c in checks),
               "fail": sum(c["status"] == "FAIL" for c in checks),
               "checks": checks}
    (OUT / "validation_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pass": summary["pass"], "fail": summary["fail"]}, ensure_ascii=False))
    if summary["fail"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
