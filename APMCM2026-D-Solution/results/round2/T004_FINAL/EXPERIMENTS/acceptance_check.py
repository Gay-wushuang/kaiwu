# -*- coding: utf-8 -*-
"""T004-08 集中验收：基线哈希、任务归档、PDF、注册表、敏感文件。只读。"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
CODE = ROOT / "code"
sys.path.insert(0, str(CODE))
from experiment_input import numeric_matrix_sha256  # noqa: E402

OUT = Path(__file__).resolve().parent / "ACCEPTANCE.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    res = {"checks": []}

    def check(name, ok, detail=""):
        res["checks"].append({"check": name, "ok": bool(ok), "detail": str(detail)})

    # 1. 基线 B 预测
    pred = ROOT / "results" / "reproduction_20261127" / "predictions"
    sums = {}
    for line in (pred / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            h, f = line.split()
            sums[f] = h
    for f, h in sums.items():
        check(f"baseline_B_hash:{f}", sha(pred / f) == h, h)

    q1 = pd.read_csv(ROOT / "results" / "reproduction_20261127" / "submission_q1_holdout.csv")
    check("Q1_holdout_rows_3703", len(q1) == 3703, len(q1))
    check("Q1_holdout_sha",
          sha(ROOT / "results" / "reproduction_20261127" / "submission_q1_holdout.csv")
          == "9395cb54a010be851007e08f61cf3f0c3361d120c1f5a14da86a17f937302b4d")

    # 2. 任务归档
    reg = json.loads((ROOT / "experiments" / "registry.json").read_text(encoding="utf-8-sig"))
    completed = [t for t in reg["tasks"] if t.get("status") == "completed"]
    check("registry_completed_7", len(completed) == 7, len(completed))
    check("registry_quota_counted_7",
          sum(1 for t in completed if t.get("quota_counted")) == 7)
    for t in completed:
        d = Path(t["archive_dir"])
        cfg = json.loads((d / "config.json").read_text(encoding="utf-8-sig"))
        meta = json.loads((d / "task.json").read_text(encoding="utf-8-sig"))
        is_pr = cfg.get("precision_method") == "precision_reducer"
        if is_pr:
            adj = np.load(d / "input" / "ising_matrix_expanded.npz")["matrix"].astype(float)
        else:
            adj = pd.read_csv(d / "input" / "ising_matrix.csv", header=None).to_numpy(float)
        check(f"submitted_hash:{t['task_name']}",
              numeric_matrix_sha256(adj) == cfg["submitted_matrix_sha256"])
        check(f"raw_solutions:{t['task_name']}", (d / "raw" / "solutions.npz").is_file())
        pdf = d / "reports" / Path(meta["report_file"]).name
        check(f"pdf:{t['task_name']}", pdf.is_file() and sha(pdf) == meta["report_sha256"])

    # 3. direct8 已知哈希
    low = next(t for t in completed if t["task_name"] == "B_Q2_k8_lowM")
    check("direct8_known_hash_34f84ed6",
          low["submitted_matrix_sha256"].startswith("34f84ed663337397"),
          low["submitted_matrix_sha256"])

    # 4. Q3 NO2 == Q2 输入
    q3 = json.loads((Path(__file__).resolve().parent / "q3_audit.json").read_text(encoding="utf-8"))
    check("Q3_NO2_reuses_Q2_matrix", q3["q3_no2_equals_q2"]["max_abs_v_diff"] == 0.0,
          q3["q3_no2_equals_q2"])

    # 5. 敏感文件
    bad = []
    for p in ROOT.rglob("*"):
        if p.is_file() and p.name.lower() in {"license.lic", "license.json", ".env"}:
            bad.append(str(p))
    check("no_license_or_env", not bad, bad)
    import subprocess
    tracked = subprocess.run(["git", "ls-files"], cwd=str(ROOT), capture_output=True,
                             text=True).stdout.splitlines()
    cache = [f for f in tracked if "__pycache__" in f or f.endswith(".pyc")]
    check("no_tracked_pycache", not cache, cache[:5])

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = all(c["ok"] for c in res["checks"])
    for c in res["checks"]:
        print(("PASS " if c["ok"] else "FAIL ") + c["check"] + ("" if c["ok"] else " :: " + c["detail"]))
    print("ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
