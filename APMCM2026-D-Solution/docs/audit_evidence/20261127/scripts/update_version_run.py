import json
from pathlib import Path

p = Path(r"e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\results\EXPERIMENT_VERSION.json")
data = json.loads(p.read_text(encoding="utf-8"))

rep = data["environments"]["original_env_replication"]
rep["status"] = "PASS"
rep["run_20261127"] = {
    "status": "PASS",
    "archive": "reproduction/original_env_20261127/run_20261127/",
    "command": "reproduction/original_env_20261127/run_reproduction.ps1",
    "workdir": "%TEMP%/apmcm_repro_original_20261127",
    "runtime_s": 17.8,
    "wall_time_s": 20.8,
    "exit_code": 0,
    "metrics": {
        "r2": 0.8248360139436758,
        "mae": 2.571641375773894,
        "rmse": 4.597197710256738,
        "spearman": 0.9353252386820915,
        "top100": 40
    },
    "submission_sha256": {
        "results/submission_q1_holdout.csv": "9395cb54a010be851007e08f61cf3f0c3361d120c1f5a14da86a17f937302b4d",
        "results/submission_q2_top20.csv": "7cf63c8ce6ea5aa921022b70c1ebe81f45e75143bd5c2688f53f36b06cbfdc9b",
        "results/submission_q3_top20.csv": "c53d633775baa265d352f0ed4903d5a78cfd87e36a2035aba57959fb8b5bb59b"
    },
    "identical_to_independent_reproduction": {
        "metrics": True,
        "submission_files": True,
        "final_answers_except_runtime": True
    },
    "differences_vs_original": "same as experiments.independent_reproduction_20261127.differences_vs_original",
    "notes": "只记录差异，不归因；04 盲测集无标签，未计算任何监督指标；未修改仓库历史产物。"
}

data["updated_at"] = "2026-11-27 Asia/Shanghai (Phase 10 supplement, reproduction run)"

data["notes"] = [
    "Original artifacts are not overwritten; reproduction outputs live in results/reproduction_20261127/.",
    "Dependency differences are recorded as observed, not asserted as the sole cause of numerical differences.",
    "No real-machine task was submitted in Phase 9; quota consumption is zero.",
    "Phase 10 supplement: original direct dependencies provided; OS still differs (Windows 11 vs Windows 10), so the environment is not claimed to be identical.",
    "Phase 10 supplement: formal reproduction run completed in the aligned environment; it matches the 3.12.6 independent reproduction exactly, while the previously recorded difference vs the original frozen results remains unexplained and unattributed."
]

p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("updated")
