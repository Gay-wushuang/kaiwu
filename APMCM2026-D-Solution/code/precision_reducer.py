# -*- coding: utf-8 -*-
"""PrecisionReducer 路线辅助：扩展矩阵捕获、拆分映射重建、解恢复与评价。

约束：
  - 不修改 SDK 行为，不读取授权凭据；只通过公开的 IsingSolver / PrecisionReducer /
    perform_precision_adaption_split / restore_split_solution / construct_split_solution
    接口工作。
  - PrecisionReducer 不公开内部 split_indices；本模块用“公开接口复现 + 比例核验”的
    方式重建映射，并记录核验证据；重建失败时明确返回 None，绝不推测。
"""
from __future__ import annotations

import numpy as np

DEFAULT_PARAMS = {
    "precision": 8,
    "target_bits": 550,
    "truncated_precision": 16,
    "only_feasible_solution": False,
}

PARAM_KEYS = set(DEFAULT_PARAMS)


def normalize_params(params=None) -> dict:
    p = dict(DEFAULT_PARAMS)
    if params:
        unknown = set(params) - PARAM_KEYS
        if unknown:
            raise ValueError(f"未知 PrecisionReducer 参数：{sorted(unknown)}")
        p.update(params)
    for k in ("precision", "truncated_precision"):
        if type(p[k]) is not int or p[k] < 1:
            raise ValueError(f"{k} 必须是正整数")
    if p["target_bits"] is not None and (type(p["target_bits"]) is not int
                                         or p["target_bits"] < 2):
        raise ValueError("target_bits 必须是 >=2 的整数或 null")
    if type(p["only_feasible_solution"]) is not bool:
        raise ValueError("only_feasible_solution 必须是布尔值")
    return p


def _capture_solver_class():
    """构造一个只记录矩阵、返回全 +1 的 IsingSolver；用于 dry-run 捕获扩展矩阵。"""
    import kaiwu as kw

    class CaptureSolver(kw.core.IsingSolver):
        def __init__(self):
            self.matrix = None
            self.preset = None

        def set_matrix(self, ising_matrix):
            self.matrix = np.asarray(ising_matrix, dtype=float)

        def on_matrix_change(self):
            pass

        def get_hamiltonian(self):
            return None

        def _solve(self, matrix):
            n = int(np.asarray(matrix).shape[0])
            if self.preset is not None:
                return np.atleast_2d(np.asarray(self.preset, dtype=float))
            return np.ones((1, n))

    return CaptureSolver


def expand_ising(ising_matrix, params=None) -> dict:
    """用 PrecisionReducer 的公开装饰器捕获实际扩展矩阵，并重建拆分映射。

    返回字段：
      params / ising_original / matrix_expanded / matrix_submitted /
      n_original / n_expanded / n_extra / split_indices / groups /
      mapping_status / mapping_evidence / bit_width / submitted_multiplier
    """
    import kaiwu.preprocess as pp

    p = normalize_params(params)
    I = np.asarray(ising_matrix, dtype=float)
    if I.ndim != 2 or I.shape[0] != I.shape[1]:
        raise ValueError("ising_matrix 必须是方阵")
    capture = _capture_solver_class()()
    pr = pp.PrecisionReducer(capture, **p)
    pr.solve(I)
    T = np.asarray(capture.matrix, dtype=float)
    if T.ndim != 2 or T.shape[0] != T.shape[1]:
        raise RuntimeError("PrecisionReducer 未给出扩展矩阵")

    Ta = np.asarray(pp.adjust_ising_matrix_precision(T, 8), dtype=float)
    bw = pp.calculate_ising_matrix_bit_width(T, 8)
    mapping = reconstruct_split(I, T, param_bit=p["precision"],
                                max_bits=min(p["truncated_precision"], 22))
    n = I.shape[0]
    if T.shape[0] == n:
        idx = np.arange(n, dtype=int)
        mapping = {"split_indices": idx, "bits": None, "denom": None, "method": "none",
                   "scale": None, "ratio_max_deviation": 0.0,
                   "status": "no_split"}
    return {
        "params": p,
        "ising_original": I,
        "matrix_expanded": T,
        "matrix_submitted": Ta,
        "n_original": int(n),
        "n_expanded": int(T.shape[0]),
        "n_extra": int(T.shape[0] - n),
        "split_indices": None if mapping is None else mapping["split_indices"],
        "groups": None if mapping is None else groups_from_indices(mapping["split_indices"]),
        "mapping_status": "unavailable" if mapping is None else mapping["status"],
        "mapping_evidence": mapping,
        "bit_width": bw,
        "submitted_multiplier": float(bw.get("multiplier", np.nan)),
        "submitted_equals_expanded": bool(np.array_equal(Ta, T)),
    }


def reconstruct_split(I, T, param_bit=8, max_bits=22):
    """用公开 split 接口复现 PrecisionReducer 的扩展矩阵，核验后返回映射。

    核验条件（全部满足才接受）：
      1. 维度相同；
      2. 非零位置完全一致；
      3. T = c * split(I_truncated)，c 为常数（相对偏差 < 1e-9）。
    失败返回 None，并保留"未验证"语义。
    """
    import kaiwu.preprocess as pp

    I = np.asarray(I, dtype=float)
    T = np.asarray(T, dtype=float)
    if I.shape != T.shape and T.ndim != 2:
        return None
    mx = float(np.abs(I).max())
    if not np.isfinite(mx) or mx == 0:
        return None
    nzT = np.abs(T) > 1e-12
    for bits in range(8, int(max_bits) + 1):
        for denom in (2 ** (bits - 1) - 1, 2 ** (bits - 1), 2 ** bits - 1):
            if denom <= 0:
                continue
            s = mx / float(denom)
            It = np.round(I / s) * s
            for method in ("var", "item"):
                try:
                    r, idx = pp.perform_precision_adaption_split(
                        It, param_bit=int(param_bit), min_increment=s, method=method)
                except Exception:
                    continue
                if r.shape != T.shape:
                    continue
                if not np.array_equal(np.abs(r) > 1e-12, nzT):
                    continue
                ratios = T[nzT] / r[nzT]
                c = float(np.median(ratios))
                dev = float(np.max(np.abs(ratios - c)))
                if dev <= 1e-9 * max(1.0, abs(c)):
                    return {
                        "split_indices": np.asarray(idx, dtype=int),
                        "bits": int(bits),
                        "denom": int(denom),
                        "method": method,
                        "scale": c,
                        "ratio_max_deviation": dev,
                        "status": "verified_reconstruction",
                    }
    return None


def groups_from_indices(split_indices):
    """按 restore_split_solution 语义，把扩展变量划为连续分组。"""
    idx = [int(v) for v in np.asarray(split_indices).ravel()]
    if not idx:
        return []
    groups = []
    prev = -1
    for last in idx:
        if last <= prev:
            raise ValueError("split_indices 必须严格递增")
        groups.append((prev + 1, last))
        prev = last
    return groups


def expanded_variables(A, B, n_original, split_indices):
    """构造扩展变量表：每个原始变量按 split_indices 的连续分组展开为多个副本。"""
    labels = [("A", str(a)) for a in A] + [("B", str(b)) for b in B]
    labels.extend([("aux", None)] * (int(n_original) - len(labels)))
    groups = groups_from_indices(split_indices)
    if len(groups) != len(labels):
        raise ValueError(f"分组数 {len(groups)} 与原始变量数 {len(labels)} 不一致")
    out = []
    for g, (a, b) in enumerate(groups):
        kind, label = labels[g]
        for copy in range(b - a + 1):
            out.append({"index": a + copy, "kind": kind, "label": label,
                        "group": g, "copy": copy})
    return out


def split_mapping_payload(exp_meta, A, B):
    """归档用的拆分映射（重建证据 + 变量表），全部字段可 JSON 序列化。"""
    idx = exp_meta.get("split_indices")
    ev = exp_meta.get("mapping_evidence") or {}
    payload = {
        "schema_version": 1,
        "precision_method": "precision_reducer",
        "params": exp_meta.get("params"),
        "n_original": exp_meta.get("n_original"),
        "n_expanded": exp_meta.get("n_expanded"),
        "n_extra": exp_meta.get("n_extra"),
        "mapping_status": exp_meta.get("mapping_status"),
        "mapping_evidence": {
            "status": ev.get("status"),
            "split_bits": ev.get("bits"),
            "denominator": ev.get("denom"),
            "method": ev.get("method"),
            "constant_scale": ev.get("scale"),
            "ratio_max_deviation": ev.get("ratio_max_deviation"),
        },
        "bit_width": exp_meta.get("bit_width"),
        "submitted_multiplier": exp_meta.get("submitted_multiplier"),
        "submitted_equals_expanded": exp_meta.get("submitted_equals_expanded"),
    }
    if idx is not None:
        payload["split_indices"] = [int(v) for v in np.asarray(idx).ravel()]
        payload["groups"] = [list(map(int, g)) for g in groups_from_indices(idx)]
        payload["variables"] = expanded_variables(A, B, exp_meta["n_original"], idx)
    else:
        payload["split_indices"] = None
        payload["groups"] = None
        payload["variables"] = None
        payload["limitation"] = "SDK 未公开 split_indices，且公开接口复现未通过核验；未推测映射。"
    return payload


def split_feasible(expanded_solutions, groups):
    """检查每组内的拆分副本是否全部相等（Ising ±1）。"""
    E = np.atleast_2d(np.asarray(expanded_solutions, dtype=float))
    mask = np.ones(E.shape[0], dtype=bool)
    for a, b in groups:
        seg = E[:, a:b + 1]
        mask &= np.all(seg == seg[:, [0]], axis=1)
    return mask


def restore_feasible(expanded_solutions, split_indices):
    """仅对拆分一致的行调用公开 restore；冲突行记为 NaN 并返回状态。"""
    import kaiwu.preprocess as pp

    E = np.atleast_2d(np.asarray(expanded_solutions, dtype=float))
    idx = np.asarray(split_indices, dtype=int)
    groups = groups_from_indices(idx)
    ok = split_feasible(E, groups)
    out = np.full((E.shape[0], len(idx)), np.nan)
    for k in range(E.shape[0]):
        if not ok[k]:
            continue
        try:
            out[k] = pp.restore_split_solution(E[k], idx)
        except Exception:
            ok[k] = False
    return out, ok


def wrap_recording_component(inner):
    """把任意 solve(matrix) 后端包装成 IsingSolver，记录 PrecisionReducer 实际传入的矩阵与返回。"""
    import kaiwu as kw

    class RecordingComponent(kw.core.IsingSolver):
        def __init__(self, component):
            self._component = component
            self.matrix = None
            self.recorded_matrix = None
            self.recorded_solutions = None
            self.solve_calls = 0

        def set_matrix(self, ising_matrix):
            self.matrix = np.asarray(ising_matrix, dtype=float)
            fn = getattr(self._component, "set_matrix", None)
            if callable(fn):
                fn(self.matrix)

        def on_matrix_change(self):
            fn = getattr(self._component, "on_matrix_change", None)
            if callable(fn):
                fn()

        def get_hamiltonian(self):
            fn = getattr(self._component, "get_hamiltonian", None)
            return fn() if callable(fn) else None

        def solve(self, *args, **kwargs):
            self.solve_calls += 1
            if args:
                self.recorded_matrix = np.asarray(args[0], dtype=float)
            elif self.matrix is not None:
                self.recorded_matrix = np.asarray(self.matrix, dtype=float)
            out = self._component.solve(*args, **kwargs)
            self.recorded_solutions = np.atleast_2d(np.asarray(out, dtype=float))
            return out

        def __getattr__(self, name):
            return getattr(self._component, name)

    return RecordingComponent(inner)


def logical_bits_from_spins(spins):
    """按相对自旋解码原始逻辑变量：x_i = (s_i * s_aux + 1) / 2。

    约定最后一列为原始辅助自旋（原始 Ising / 恢复后的原始向量均如此）。
    全局翻转 s -> -s 不改变 x；单独翻转辅助自旋会改变 x，不能视为同一逻辑状态。
    这是唯一允许的原始维度解码口径；扩展矩阵不能直接套用（末位不是原始辅助自旋）。
    """
    s = np.atleast_2d(np.asarray(spins, dtype=float))
    if s.ndim != 2 or s.shape[1] < 2:
        raise ValueError(f"自旋向量必须为二维且至少 2 列：shape={s.shape}")
    if not np.all(np.isfinite(s)):
        raise ValueError("自旋向量含非有限值（恢复冲突行不能解码）")
    aux = s[:, [-1]]
    x = (s[:, :-1] * aux + 1.0) / 2.0
    if not np.allclose(x, np.round(x), atol=1e-9):
        raise ValueError("相对自旋解码未得到 0/1")
    return np.round(x).astype(int)


def logical_labels_from_spins(spins, nA, nB):
    """返回每行的 (i, j) 或 None；只认恰好一个 A、一个 B 的 one-hot。"""
    bits = logical_bits_from_spins(spins)
    out = []
    for row in bits:
        ia = [i for i in range(nA) if row[i] == 1]
        ib = [i - nA for i in range(nA, nA + nB) if row[i] == 1]
        out.append((ia[0], ib[0]) if len(ia) == 1 and len(ib) == 1 else None)
    return out


def evaluate_restored(restored, V, A, B):
    """对恢复后的原始自旋逐行解码，返回合法性、标签与原始目标值。

    使用相对自旋口径，原始辅助自旋在末位；扩展矩阵必须先恢复再解码。
    """
    V = np.asarray(V, dtype=float)
    nA, nB = V.shape
    R = np.atleast_2d(np.asarray(restored, dtype=float))
    rows = []
    for k, s in enumerate(R):
        if not np.all(np.isfinite(s)):
            rows.append({"sample": k, "legal": False, "reason": "restore_conflict"})
            continue
        try:
            bits = logical_bits_from_spins(s)[0][:nA + nB]
        except ValueError:
            rows.append({"sample": k, "legal": False, "reason": "decode_error"})
            continue
        ia = [i for i in range(nA) if bits[i] == 1]
        ib = [i - nA for i in range(nA, nA + nB) if bits[i] == 1]
        if len(ia) == 1 and len(ib) == 1:
            rows.append({"sample": k, "legal": True, "i": int(ia[0]), "j": int(ib[0]),
                         "A": A[ia[0]], "B": B[ib[0]], "V": float(V[ia[0], ib[0]])})
        else:
            rows.append({"sample": k, "legal": False, "reason": "onehot_violation"})
    return rows
