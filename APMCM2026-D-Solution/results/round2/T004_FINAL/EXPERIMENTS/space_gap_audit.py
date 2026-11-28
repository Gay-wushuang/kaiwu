# -*- coding: utf-8 -*-
"""T004-04 约束有效性：所有 direct8 真机实例的全空间合法/非法最低能量（精确）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import q3_audit as QA            # noqa: E402

TASKS = ROOT / "experiments" / "tasks"
OUT = Path(__file__).resolve().parent / "space_gap_audit.json"


def main():
    rows = []
    for d in sorted(TASKS.iterdir()):
        tj = d / "task.json"
        if not tj.is_file():
            continue
        task = json.loads(tj.read_text(encoding="utf-8-sig"))
        if task.get("status") != "completed":
            continue
        cfg = json.loads((d / "config.json").read_text(encoding="utf-8-sig"))
        if cfg.get("precision_method") == "precision_reducer":
            continue
        adj = pd.read_csv(d / "input" / "ising_matrix.csv", header=None).to_numpy(float)
        n = int(cfg["topk"])
        r = QA.exact_submitted_space(adj, n, n)
        r.update(task_name=task["task_name"], n_ising=int(adj.shape[0]),
                 topk=n, matrix_sha256=cfg["submitted_matrix_sha256"])
        rows.append(r)
    out = {"scope": "exact full-space logical enumeration of submitted direct8 Ising matrices",
           "note": "逻辑变量 x_i=(s_i*s_aux+1)/2；固定 aux=+1 规范代表枚举全部逻辑状态。"
                   "s 与 -s 是同一逻辑状态的两个物理代表，能量相同，不产生新的逻辑状态。",
           "rows": rows}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in rows:
        print(f"{r['task_name']:24s} n={r['n_ising']:3d} "
              f"legal={r['min_legal_logical']:9.1f} illegal={r['min_illegal_logical']:9.1f} "
              f"gap={r['gap_logical']:7.1f} all_legal={r['ground_state_all_logical_legal']}")


if __name__ == "__main__":
    main()
