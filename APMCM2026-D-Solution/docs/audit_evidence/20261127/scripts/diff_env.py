import re
from pathlib import Path

ROOT = Path(r"e:\ERE\Documents\Work\开物量子\APMCM2026-D-Solution")
REQ = ROOT / "docs/reproduction/original_environment/requirements.txt"
LOCK = ROOT / "requirements.lock.txt"
FREEZE = ROOT / "docs/reproduction/original_environment/requirements.freeze.txt"


def parse(path, skip_comments=True):
    out = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or (skip_comments and line.startswith("#")):
            continue
        if "==" in line:
            k, v = line.split("==", 1)
            out[k.strip().lower()] = v.strip()
    return out


req = parse(REQ)
lock = parse(LOCK)
new = parse(FREEZE)

print("## 直接依赖对照\n")
print("| 包 | 队友要求 | requirements.lock (kaiwu-verify) | kaiwu-original 实测 | 判定 |")
print("|---|---:|---:|---:|---|")
for k, v in req.items():
    lv = lock.get(k, "未安装")
    nv = new.get(k, "未安装")
    if lv == v and nv == v:
        status = "一致"
    elif lv != v and nv == v:
        status = "kaiwu-verify 不同；新环境已对齐"
    elif lv == v and nv != v:
        status = "kaiwu-verify 一致；新环境不同"
    else:
        status = "需复核"
    print(f"| {k} | {v} | {lv} | {nv} | {status} |")

print("\n## 全量包差异（kaiwu-verify 与新环境）\n")
only_lock = sorted(set(lock) - set(new))
only_new = sorted(set(new) - set(lock))
diffs = sorted(k for k in set(lock) & set(new) if lock[k] != new[k])
print("| 类别 | 包 | 说明 |")
print("|---|---|---|")
for k in only_lock:
    print(f"| 仅旧环境 | {k} | {lock[k]} |")
for k in only_new:
    print(f"| 仅新环境 | {k} | {new[k]} |")
for k in diffs:
    print(f"| 版本不同 | {k} | {lock[k]} → {new[k]} |")

print(f"\n包数：requirements {len(req)} | lock {len(lock)} | new {len(new)}")
