import json
from pathlib import Path

p = Path(r"e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution\results\EXPERIMENT_VERSION.json")
data = json.loads(p.read_text(encoding="utf-8"))

data["updated_at"] = "2026-11-27 Asia/Shanghai (Phase 10 supplement)"

data["environments"]["original_solution_env"] = {
    "status": "PROVIDED_PARTIAL",
    "provided_at": "2026-11-27",
    "source": "docs/reproduction/original_environment/",
    "claimed": {
        "python": "3.12.5",
        "os": "Windows 11",
        "direct_dependencies": {
            "numpy": "2.4.4",
            "pandas": "2.2.3",
            "scikit-learn": "1.8.0",
            "xgboost": "3.4.1",
            "lightgbm": "4.7.0",
            "mendeleev": "1.4.0",
            "scipy": "1.17.1",
            "matplotlib": "3.10.3",
            "kaiwu": "1.4.4"
        }
    },
    "archived_files": {
        "REPRO_NOTES.md": "e601b556065bb3bf061223a027a575bc5f8aa16e7b2a8df81411271035cff9c9",
        "requirements.txt": "fe0fd99f3f9fbfb145e34a6b02384555f26b2b39281aed249e01273e30b9f479",
        "same_protocol_metrics.json": "20a68f7df3bf6c4b7755d300b79f6e39cf669c426b45da2f26cd9a51b90728e7"
    },
    "transitive_dependencies": "NOT_PROVIDED",
    "notes": "队友提供 9 个直接依赖与复现说明；传递依赖未提供，无法逐包核对。"
}

data["environments"]["original_env_replication"] = {
    "status": "PARTIAL_PASS",
    "path": "%LOCALAPPDATA%/kaiwu-original",
    "python": "3.12.5",
    "platform": "Windows-10-10.0.19045-SP0",
    "claimed_platform": "Windows 11",
    "os_match": False,
    "pip": "26.3",
    "installer": "独立 CPython 3.12.5（uv 管理）+ pip -r requirements.txt",
    "lock_file": "docs/reproduction/original_environment/requirements.freeze.txt",
    "pip_check": "No broken requirements found.",
    "import_check": "docs/reproduction/original_environment/import_check.json",
    "imports_ok": "10/10",
    "differences_vs_kaiwu_verify": {
        "only_in_new": {"lightgbm": "4.7.0"},
        "version_diff": {
            "numpy": ["2.5.5", "2.4.4"],
            "scikit-learn": ["1.9.1", "1.8.0"],
            "scipy": ["1.18.1", "1.17.1"]
        },
        "note": "其余 51 个传递依赖版本一致"
    },
    "notes": "Python 精确匹配；操作系统不同；不得宣称与队友环境完全相同。未修改 kaiwu-verify。"
}

data["evaluation_protocols"] = {
    "P1_validation_02_to_03": {
        "train": "date/02_castelli_train.csv (11,256 rows)",
        "validation": "date/03_castelli_val.csv (3,969 rows)",
        "grouping": "(A,B) element pairs, disjoint between train and validation",
        "locally_computable": True,
        "metrics_source": "REPRO_NOTES.md section 2; results/model_compare.csv; results/metrics.csv",
        "usage": "论文表 2 与全部论文指标"
    },
    "P2_grouped_oof": {
        "data": "02+03, 15,225 rows",
        "grouping": "GroupKFold(5) by (A,B)",
        "locally_computable": "requires team's split implementation; no repository script",
        "metrics_source": "same_protocol_metrics.json",
        "metrics": {
            "rmse": 4.612290573356756,
            "spearman": 0.9384828696112181,
            "ndcg100": 0.02013819485609915
        },
        "usage": "仅参考，不用于论文结论"
    },
    "P3_official_blind_04": {
        "data": "date/04_castelli_test_holdout.csv (3,703 rows, 6 columns, no V label)",
        "locally_computable": False,
        "output": "results/submission_q1_holdout.csv",
        "usage": "问题 1 最终提交；指标只能由官方评分得到"
    }
}

supplements = data.setdefault("supplements", [])
supplements.append({
    "phase": "Phase 10 supplement",
    "date": "2026-11-27",
    "item": "original environment alignment",
    "report": "docs/reproduction/original_environment/ENVIRONMENT_REPORT.md",
    "protocols": "docs/reproduction/PROTOCOLS.md",
    "status": "PARTIAL_PASS",
    "boundary": "未修改模型/算法/参数/种子；未提交真机任务；未消耗配额"
})

data["notes"] = [
    "Original artifacts are not overwritten; reproduction outputs live in results/reproduction_20261127/.",
    "Dependency differences are recorded as observed, not asserted as the sole cause of numerical differences.",
    "No real-machine task was submitted in Phase 9; quota consumption is zero.",
    "Phase 10 supplement: original direct dependencies provided; OS still differs (Windows 11 vs Windows 10), so the environment is not claimed to be identical."
]

p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("updated", p)
