import hashlib
import json
from pathlib import Path

ROOT = Path(r"e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution")
WORK = Path(r"C:\Users\ERE.DESKTOP-JD48OPB\AppData\Local\Temp\apmcm_repro_original_20261127")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def diff(a, b, path=""):
    out = []
    if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return [(path or "/", a, b)]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((f"{path}/{k}", a.get(k, "<missing>"), b.get(k, "<missing>")))
            else:
                out.extend(diff(a[k], b[k], f"{path}/{k}"))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((f"{path}/len", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff(x, y, f"{path}[{i}]"))
    else:
        if a != b:
            out.append((path or "/", a, b))
    return out


ours = json.loads((WORK / "results/final_answers.json").read_text(encoding="utf-8"))
repro = json.loads((ROOT / "results/reproduction_20261127/final_answers.json").read_text(encoding="utf-8"))
orig = json.loads((ROOT / "results/final_answers.json").read_text(encoding="utf-8"))

print("## final_answers.json 差异（忽略 runtime_s）\n")
for label, base in (("独立复现 3.12.6", repro), ("仓库原始", orig)):
    a = dict(base)
    a.pop("runtime_s", None)
    b = dict(ours)
    b.pop("runtime_s", None)
    d = diff(a, b)
    print(f"### 复跑 vs {label}")
    if not d:
        print("除 runtime_s 外完全一致。")
    else:
        for path, x, y in d:
            print(f"- {path}: {x!r} → {y!r}")
    print()

print("## 关键指标\n")
print("| 指标 | 复跑 (3.12.5 原始依赖) | 独立复现 (3.12.6) | 仓库原始 |")
print("|---|---:|---:|---:|")
for k in ("r2", "mae", "rmse", "spearman", "top100"):
    print(f"| {k} | {ours['validate'][k]} | {repro['validate'][k]} | {orig['validate'][k]} |")
print(f"| runtime_s | {ours.get('runtime_s')} | {repro.get('runtime_s')} | {orig.get('runtime_s')} |")

print("\n## 交付文件 SHA256\n")
print("| 文件 | 复跑 | 独立复现 3.12.6 | 仓库原始 | 与独立复现一致 |")
print("|---|---|---|---|---|")
for name in ("submission_q1_holdout.csv", "submission_q2_top20.csv", "submission_q3_top20.csv"):
    h_ours = sha(WORK / "results" / name)
    p_repro = ROOT / "results/reproduction_20261127" / name
    p_orig = ROOT / "results" / name
    h_repro = sha(p_repro) if p_repro.is_file() else "MISSING"
    h_orig = sha(p_orig) if p_orig.is_file() else "MISSING"
    print(f"| {name} | {h_ours[:16]}… | {h_repro[:16]}… | {h_orig[:16]}… | {h_ours == h_repro} |")

print("\n## 预测文件（pool_*_phys）复跑 vs 仓库原始\n")
same = 0
different = 0
for p in sorted((WORK / "code/predictions").glob("*_phys.csv")):
    q = ROOT / "code/predictions" / p.name
    h1 = sha(p)
    h2 = sha(q) if q.is_file() else "MISSING"
    flag = h1 == h2
    same += flag
    different += (not flag)
    print(f"- {p.name}: {'一致' if flag else '不同'} ({h1[:12]}… vs {str(h2)[:12]}…)")
print(f"\n一致 {same} 个，不同 {different} 个")
