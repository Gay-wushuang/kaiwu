import importlib
import importlib.metadata as md
import json
import os
import platform
import sys
from pathlib import Path

MODULES = ["numpy", "pandas", "sklearn", "xgboost", "lightgbm", "mendeleev",
           "scipy", "matplotlib", "joblib", "kaiwu"]
DIST_NAME = {"sklearn": "scikit-learn", "kaiwu": "kaiwu"}

result = {
    "python": sys.version,
    "platform": platform.platform(),
    "executable": sys.executable,
    "modules": {},
}

for m in MODULES:
    entry = {}
    try:
        importlib.import_module(m)
        entry["import"] = "OK"
        try:
            entry["version"] = md.version(DIST_NAME.get(m, m))
        except Exception as e:
            entry["version"] = None
            entry["version_error"] = str(e)
    except Exception as e:
        entry["import"] = "FAIL"
        entry["error"] = f"{type(e).__name__}: {e}"
    result["modules"][m] = entry

try:
    import kaiwu as kw
    result["modules"]["kaiwu"]["attribute_version"] = getattr(kw, "__version__", None)
    result["license_module_present"] = hasattr(kw, "license")
except Exception as e:
    result["license_module_present"] = None
    result["kaiwu_error"] = f"{type(e).__name__}: {e}"

# 只检查授权文件是否存在，不读取、不打印内容
candidates = [
    Path.home() / ".kaiwu",
    Path(os.environ.get("APPDATA", "")) / "kaiwu",
    Path(os.environ.get("LOCALAPPDATA", "")) / "kaiwu",
]
result["license_paths"] = []
for p in candidates:
    if not str(p):
        continue
    exists = p.exists()
    n_files = 0
    if exists:
        try:
            n_files = sum(1 for x in p.rglob("*") if x.is_file())
        except Exception:
            n_files = -1
    result["license_paths"].append({"path": str(p), "exists": exists, "file_count": n_files})

out = Path(sys.argv[1])
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
