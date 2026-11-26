r"""环境自检：版本、依赖、模块、license 依赖状态。

用法：
    environment\.venv\Scripts\python.exe environment\verify_env.py

退出码 0 表示"环境可用"（license 缺失不算环境失败，会单独标为 BLOCKED）。
"""

import importlib.metadata as md
import json
import platform
import subprocess
import sys
from pathlib import Path

REQUIRED_PY = {(3, 10), (3, 12), (3, 14)}
EXPECTED_KAIWU = "1.4.4"

PROBE = r"""
import json, numpy as np, kaiwu as kw
res = {}
m = -np.array([[0.,1.,0.,1.,1.],[1.,0.,0.,1.,1.],[0.,0.,0.,1.,1.],[1.,1.,1.,0.,1.],[1.,1.,1.,1.,0.]])
def probe(name, fn):
    try:
        fn(); res[name] = "PASS"
    except (EOFError, ValueError) as e:
        res[name] = "BLOCKED_LICENSE"
    except Exception as e:
        res[name] = f"{type(e).__name__}"
probe("BruteForceOptimizer", lambda: kw.classical.BruteForceOptimizer().solve(m))
probe("TabuSearchOptimizer", lambda: kw.classical.TabuSearchOptimizer(100, size_limit=1).solve(m))
probe("SimulatedAnnealingSampler",
      lambda: kw.sampler.SimulatedAnnealingSampler(alpha=0.99, cutoff_temperature=0.001,
                                                   iterations_per_t=10).solve(m))
probe("SimulatedAnnealingOptimizer",
      lambda: kw.classical.SimulatedAnnealingOptimizer(size_limit=5).solve(m))
print("RESULT_JSON:" + json.dumps(res, ensure_ascii=False))
"""


def main():
    ok = True
    print("=" * 66)
    print("Kaiwu SDK 环境自检")
    print("=" * 66)
    print(f"操作系统 : {platform.platform()}")
    print(f"Python   : {platform.python_version()} ({platform.architecture()[0]})")
    print(f"解释器   : {sys.executable}")

    if sys.version_info[:2] not in REQUIRED_PY:
        print("!! Python 小版本不在官方声明范围 (3.10/3.12/3.14)")
        ok = False
    else:
        print("Python 版本: PASS")

    try:
        import kaiwu as kw  # noqa: F401
    except Exception as exc:
        print(f"!! kaiwu 导入失败: {type(exc).__name__}: {exc}")
        print("结论: FAIL")
        raise SystemExit(1)
    print("kaiwu 导入: PASS")

    version = md.version("kaiwu")
    print(f"kaiwu 发行版版本: {version}")
    print(f"kw.__version__ (注意: 来自 kaiwu-community): {getattr(kw, '__version__', None)}")
    if version != EXPECTED_KAIWU:
        print(f"!! 版本与预期 {EXPECTED_KAIWU} 不一致")
        ok = False

    for name in ["numpy", "pandas", "matplotlib", "kaiwu-community"]:
        try:
            print(f"  {name}: {md.version(name)}")
        except md.PackageNotFoundError:
            print(f"  !! 缺少依赖: {name}")
            ok = False

    required_attrs = ["core", "classical", "cim", "preprocess", "sampler", "hybrid", "hobo", "license"]
    missing = [a for a in required_attrs if not hasattr(kw, a)]
    if missing:
        print(f"!! 缺少模块: {missing}")
        ok = False
    else:
        print(f"模块完整性: PASS ({', '.join(required_attrs)})")

    proc = subprocess.run(
        [sys.executable, "-c", PROBE], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300
    )
    solvers = {}
    for line in proc.stdout.splitlines():
        marker = line.find("RESULT_JSON:")
        if marker >= 0:
            solvers = json.loads(line[marker + len("RESULT_JSON:"):])
    print("求解器 license 依赖（实测）:")
    for name, status in solvers.items():
        print(f"  {name}: {status}")

    out = Path(__file__).resolve().parent / "verify_env_result.json"
    out.write_text(
        json.dumps(
            {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "kaiwu": version,
                "solvers": solvers,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"结果已写入: {out}")
    print("结论: " + ("PASS（license 状态见上）" if ok else "FAIL"))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
