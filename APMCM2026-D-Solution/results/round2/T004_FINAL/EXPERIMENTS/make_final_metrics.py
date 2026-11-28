# -*- coding: utf-8 -*-
"""从 T004 的 JSON 证据生成 FINAL_METRICS.csv（长表）。"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "FINAL_METRICS.csv"
ROOT = HERE.parents[3]


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main():
    tasks = load("task_audit.json")
    q3 = load("q3_audit.json")
    cost = load("route_cost.json")
    gaps = load("space_gap_audit.json")["rows"]
    q1 = json.loads((ROOT / "results" / "reproduction_20261127" / "final_answers.json")
                    .read_text(encoding="utf-8"))["validate"]
    q3df = pd.read_csv(ROOT / "results" / "reproduction_20261127" / "predictions"
                       / "pool_q3_phys.csv")
    fmap = {(str(a), str(b), str(x)): str(f) for a, b, x, f in
            q3df[["A", "B", "X", "formula"]].itertuples(index=False, name=None)}

    rows = []

    def add(section, subject, metric, value, unit="", source="", level="", note=""):
        rows.append(dict(section=section, subject=subject, metric=metric, value=value,
                         unit=unit, source=source, evidence_level=level, note=note))

    # Q1
    add("Q1", "baseline_B", "r2", q1["r2"], "", "reproduction_20261127/final_answers.json",
        "verified", "02 train / 03 validation")
    add("Q1", "baseline_B", "mae", q1["mae"], "", "same", "verified", "")
    add("Q1", "baseline_B", "rmse", q1["rmse"], "", "same", "verified", "")
    add("Q1", "baseline_B", "spearman", q1["spearman"], "", "same", "verified", "")
    add("Q1", "baseline_B", "top100_hits", q1["top100"], "of 100", "same", "verified", "")
    add("Q1", "baseline_B", "holdout_rows", 3703, "rows",
        "results/reproduction_20261127/submission_q1_holdout.csv", "verified",
        "SHA256 9395cb54a010be851007e08f61cf3f0c3361d120c1f5a14da86a17f937302b4d")

    # Q2 原始最优
    add("Q2", "baseline_B", "raw_argmin", "LaZrO2N", "", "reproduction_20261127/predictions/pool_q2_phys.csv",
        "verified", "V_hat=0")
    add("Q2", "baseline_B", "second_best", "LaHfO2N", "", "same", "verified", "V_hat=0.001396369617951")

    # Q3 聚合
    g = q3["q3_global"]
    add("Q3", "baseline_B", "global_raw_min", g["raw_min"], "", "q3_audit.json", "verified",
        "full 8112")
    add("Q3", "baseline_B", "global_argmin_count", g["argmin_count"], "candidates", "q3_audit.json",
        "verified", "O3=3, NO2=1, FO2=2")
    add("Q3", "baseline_B", "global_argmin_list",
        " | ".join(fmap.get((a, b, x), f"{a}-{b}-{x}") for a, b, x in g["argmin_list"]),
        "", "q3_audit.json", "verified", "")
    for x, r in q3["per_x"].items():
        add("Q3", f"{x}_slice", "raw_min", r.get("raw_min"), "", "q3_audit.json", "verified", "")
        add("Q3", f"{x}_slice", "raw_argmin",
            ";".join(fmap.get((a, b, x), f"{a}-{b}") for a, b, _ in r.get("raw_argmin_top", [])),
            "", "q3_audit.json", "verified", "")
        add("Q3", f"{x}_slice", "topk_retains_all_raw", r.get("topk_retains_all_raw_argmins"), "bool",
            "q3_audit.json", "verified", "")
        add("Q3", f"{x}_slice", "quantized_full_legal_set_size",
            len(r.get("quantized_full_legal_set") or []), "labels", "q3_audit.json", "verified", "")
        add("Q3", f"{x}_slice", "quantized_full_retention", r.get("quantized_full_retention"), "fraction",
            "q3_audit.json", "verified", "")
        add("Q3", f"{x}_slice", "quantized_topk_legal_set_size",
            len(r.get("quantized_topk_legal_set") or []), "labels", "q3_audit.json", "verified", "")
        add("Q3", f"{x}_slice", "quantized_topk_retention", r.get("quantized_topk_retention"), "fraction",
            "q3_audit.json", "verified", "")
        add("Q3", f"{x}_slice", "quantized_topk_extra", r.get("quantized_topk_extra"), "labels",
            "q3_audit.json", "verified", "")
        add("Q3", f"{x}_slice", "quantized_topk_spearman", r.get("quantized_topk_spearman"), "",
            "q3_audit.json", "verified", "")
        sp = r.get("submitted_space_exact") or {}
        add("Q3", f"{x}_slice", "full_space_gap_aux_plus", sp.get("gap_aux_plus"), "H units",
            "q3_audit.json", "verified", "aux=+1 binary domain")
        add("Q3", f"{x}_slice", "full_space_gap_anyaux", sp.get("gap_anyaux"), "H units",
            "q3_audit.json", "verified", "Z2 complement degeneracy")

    # 真机任务逐项
    for t in tasks:
        subj = t["task_name"]
        for metric, value, unit in (
            ("task_id", t["task_id"], ""),
            ("platform_task_id", t.get("platform_task_id"), ""),
            ("device", t.get("device"), ""),
            ("precision_method", t.get("precision_method") or "direct_8bit", ""),
            ("topk", t.get("topk"), ""),
            ("n_qubo", t.get("n_qubo"), "bits"),
            ("n_ising_original", t.get("n_ising_original") or t.get("n_ising"), "spins"),
            ("n_submitted", t.get("n_ising"), "spins"),
            ("extra_split_spins", t.get("split_extra_spins") or 0, "spins"),
            ("returned", t.get("returned"), "samples"),
            ("legal", t.get("legal"), "samples"),
            ("split_feasible", t.get("split_feasible"), "samples"),
            ("both", t.get("both"), "samples"),
            ("strict_original_optimum_hit", t.get("strict_hit"), "samples"),
            ("best_legal_V", t.get("best_legal_V"), ""),
            ("best_strict_V", t.get("best_strict_V"), ""),
            ("hardware_ms", t.get("hardware_ms"), "ms"),
            ("e2e_s", t.get("runtime_s"), "s"),
            ("quota_units", 1, "task"),
            ("input_matrix_sha256", t.get("input_matrix_sha256"), ""),
            ("submitted_matrix_sha256", t.get("submitted_matrix_sha256"), ""),
        ):
            add("REAL_MACHINE", subj, metric, value, unit, t["task_id"], "observed", "")
        if t.get("quantized_legal_set") is not None:
            add("REAL_MACHINE", subj, "quantized_legal_set_size", len(t["quantized_legal_set"]),
                "labels", t["task_id"], "verified", "")
            add("REAL_MACHINE", subj, "quantized_retention", t.get("quantized_retention"),
                "fraction", t["task_id"], "verified", "")
            add("REAL_MACHINE", subj, "quantized_extra", t.get("quantized_extra"),
                "labels", t["task_id"], "verified", "")

    # 成本
    for route, v in cost["Q2"].items():
        add("COST_LOCAL", route, "n_submitted", v["n_submitted"], "spins", "route_cost.json", "measured", "")
        add("COST_LOCAL", route, "build_ms_median", round(v["build_s_median"] * 1000, 4), "ms",
            "route_cost.json", "measured", "5 repeats")
        add("COST_LOCAL", route, "adapt_ms_median", round(v["adapt_s_median"] * 1000, 4), "ms",
            "route_cost.json", "measured", "5 repeats")
    for x, routes in cost["Q3"].items():
        for route, v in routes.items():
            add("COST_LOCAL", f"Q3_{x}_{route}", "n_submitted", v["n_submitted"], "spins",
                "route_cost.json", "measured", "")
            add("COST_LOCAL", f"Q3_{x}_{route}", "build_ms_median", round(v["build_s_median"] * 1000, 4),
                "ms", "route_cost.json", "measured", "")
            add("COST_LOCAL", f"Q3_{x}_{route}", "adapt_ms_median", round(v["adapt_s_median"] * 1000, 4),
                "ms", "route_cost.json", "measured", "")

    # 全空间间隙
    for r in gaps:
        add("SPACE_GAP", r["task_name"], "legal_min_H_aux_plus", r["min_legal_aux_plus"], "H",
            "space_gap_audit.json", "verified", "2^26 or 2^16 exact")
        add("SPACE_GAP", r["task_name"], "illegal_min_H_aux_plus", r["min_illegal_aux_plus"], "H",
            "space_gap_audit.json", "verified", "")
        add("SPACE_GAP", r["task_name"], "gap_aux_plus", r["gap_aux_plus"], "H",
            "space_gap_audit.json", "verified", "")
        add("SPACE_GAP", r["task_name"], "gap_anyaux", r["gap_anyaux"], "H",
            "space_gap_audit.json", "verified", "Z2 degeneracy")

    # 候选
    cand = load("CANDIDATE_LOCAL_EVIDENCE.json")
    for name, v in cand.items():
        add("CANDIDATE", name, "n_submitted", v["n_submitted"], "spins",
            "CANDIDATE_LOCAL_EVIDENCE.json", "dry_run", "not submitted")
        add("CANDIDATE", name, "matrix_sha256", v["matrix_sha256"], "",
            "CANDIDATE_LOCAL_EVIDENCE.json", "dry_run", "")
        add("CANDIDATE", name, "quantized_retention", v.get("retention"), "fraction",
            "CANDIDATE_LOCAL_EVIDENCE.json", "verified_local",
            "原始 V̂ 最优是否在量化合法最优集合内")
        add("CANDIDATE", name, "expected_quota", 1, "task",
            "REAL_MACHINE_CANDIDATES/SUBMISSION_LIST.md", "dry_run",
            "not submitted; recommendation: do not spend quota")

    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["section", "subject", "metric", "value", "unit",
                                          "source", "evidence_level", "note"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT} rows={len(rows)}")


if __name__ == "__main__":
    main()
