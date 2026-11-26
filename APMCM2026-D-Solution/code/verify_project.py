# -*- coding: utf-8 -*-
"""工程验收自检：依赖、输入、入口、输出、SHA256、路径可移植性、dry-run 安全性。

不联网、不调用 license、不创建云端任务、不消耗配额。
用法：python code/verify_project.py
退出码：0 = 工程检查通过（数据缺失只记为 BLOCKED）；1 = 存在 FAIL。
"""
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

from paths import DATA, DATA_FILES, MODELS, PRED, RES, ROOT

CODE = ROOT / "code"
MANIFEST = RES / "ARTIFACT_SHA256.json"

REQUIRED_DEPS = ("kaiwu", "numpy", "pandas", "sklearn", "xgboost",
                 "mendeleev", "scipy", "joblib", "matplotlib")
OPTIONAL_DEPS = ("lightgbm",)

# 输出文件最低要求：路径 -> 期望行数（None 表示只要求存在）
EXPECTED_OUTPUTS = {
    RES / "submission_q1_holdout.csv": 3703,
    RES / "submission_q2_top20.csv": 20,
    RES / "submission_q3_top20.csv": 20,
    RES / "final_answers.json": None,
    RES / "FINAL_ANSWERS.md": None,
    RES / "metrics.csv": None,
    RES / "metrics.json": None,
    RES / "val_predictions.csv": 3969,
    RES / "model_compare.csv": None,
    RES / "local_sa_stats.csv": None,
}

REQUIRED_PREDICTIONS = (
    "pool_q2_phys.csv", "pool_q3_phys.csv", "pool_q2b_phys.csv", "pool_q3b_phys.csv",
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    fail, blocked, warn, ok = [], [], [], []

    # 1) 依赖
    print("=" * 66)
    print("[1] 依赖完整性")
    for name in REQUIRED_DEPS:
        found = importlib.util.find_spec(name) is not None
        print(f"  {name:12s}: {'OK' if found else 'MISSING'}")
        (ok if found else fail).append(f"依赖 {name}")
    for name in OPTIONAL_DEPS:
        found = importlib.util.find_spec(name) is not None
        print(f"  {name:12s}: {'OK' if found else 'MISSING（可选）'}")
        if not found:
            warn.append(f"可选依赖 {name} 未安装")

    # 2) 原始数据
    print("=" * 66)
    print("[2] 输入数据（赛题附件）")
    missing_data = [n for n in DATA_FILES if not (DATA / n).is_file()]
    if missing_data:
        print(f"  BLOCKED：{len(missing_data)}/8 个文件缺失，目录 {DATA}")
        for n in missing_data:
            print(f"    - {n}")
        blocked.append("赛题附件缺失（问题 1 与 run_all 不可运行）")
    else:
        print("  8/8 个附件存在")
        ok.append("赛题附件完整")

    # 3) 预测与模型文件
    print("=" * 66)
    print("[3] 预测与模型文件")
    for n in REQUIRED_PREDICTIONS:
        p = PRED / n
        print(f"  {n:22s}: {'OK' if p.is_file() else 'MISSING'}")
        if not p.is_file():
            fail.append(f"预测文件 {n}")
    model = MODELS / "surrogate_phys.joblib"
    print(f"  models/surrogate_phys.joblib: {'OK' if model.is_file() else 'MISSING（可由 run_all.py 生成）'}")
    if not model.is_file():
        blocked.append("代理模型 joblib 未生成（需先补齐数据）")

    # 4) 程序入口：语法编译
    print("=" * 66)
    print("[4] 程序入口语法检查")
    for p in sorted(CODE.glob("*.py")):
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as e:
            print(f"  FAIL {p.name}: {e}")
            fail.append(f"语法错误 {p.name}")
    print(f"  已检查 {len(list(CODE.glob('*.py')))} 个脚本")
    ok.append("脚本语法")

    # 5) 路径可移植性：禁止盘符绝对路径与 sys.path 注入
    print("=" * 66)
    print("[5] 路径可移植性")
    pattern = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:\\")
    bad = []
    for p in sorted(CODE.glob("*.py")):
        if p.name == "verify_project.py":   # 本文件含检测规则字面量，跳过自检
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line) or "sys.path.insert" in line:
                bad.append(f"{p.name}:{i}: {line.strip()}")
    if bad:
        for b in bad:
            print(f"  FAIL {b}")
        fail.append("存在硬编码绝对路径")
    else:
        print("  未发现盘符绝对路径或 sys.path 注入")
        ok.append("路径可移植性")

    # 6) 输出文件
    print("=" * 66)
    print("[6] 输出文件完整性")
    for p, rows in EXPECTED_OUTPUTS.items():
        if not p.is_file():
            print(f"  MISSING {p.relative_to(ROOT)}")
            fail.append(f"输出缺失 {p.name}")
            continue
        text_rows = None
        if p.suffix == ".csv":
            with open(p, encoding="utf-8-sig") as f:
                text_rows = sum(1 for _ in f) - 1
        flag = ""
        if rows is not None and text_rows != rows:
            flag = f"（期望 {rows}，实际 {text_rows}）"
            fail.append(f"行数不符 {p.name}")
        print(f"  OK {p.relative_to(ROOT)}{flag}")
    if all(p.is_file() for p in EXPECTED_OUTPUTS):
        ok.append("输出文件")

    # 7) dry-run 安全性（子进程，关闭 stdin，不会进入 license 流程）
    print("=" * 66)
    print("[7] dry-run 安全性")
    proc = subprocess.run(
        [sys.executable, str(CODE / "d_run_stats.py"),
         "--task-name", "verify_dryrun", "--topk", "13", "--mode", "opt", "--dry-run"],
        cwd=str(ROOT), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    dry_ok = proc.returncode == 0 and "[DRY-RUN]" in out and "Please enter user ID" not in out
    print(f"  退出码 {proc.returncode} | 输出含 DRY-RUN：{'[DRY-RUN]' in out} | "
          f"未触发 license 输入：{'Please enter user ID' not in out}")
    if dry_ok:
        print("  PASS：dry-run 未创建云端任务、未进入授权流程")
        ok.append("dry-run 安全性")
    else:
        print("  FAIL：dry-run 行为不符合预期")
        fail.append("dry-run 安全性")

    # 8) SHA256 清单
    print("=" * 66)
    print("[8] SHA256 校验")
    if not MANIFEST.is_file():
        print(f"  BLOCKED：清单不存在 {MANIFEST}")
        blocked.append("SHA256 清单缺失")
    else:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        mismatch = []
        for rel, expected in manifest.get("files", {}).items():
            p = ROOT / rel
            if not p.is_file():
                mismatch.append(f"{rel}: MISSING")
            elif sha256(p) != expected:
                mismatch.append(f"{rel}: HASH_DIFF")
        if mismatch:
            for m in mismatch:
                print(f"  FAIL {m}")
            fail.append(f"SHA256 不一致 {len(mismatch)} 项")
        else:
            print(f"  PASS：{len(manifest.get('files', {}))} 个文件哈希一致")
            ok.append("SHA256")

    # 汇总
    print("=" * 66)
    print(f"结论：PASS {len(ok)} 项 | FAIL {len(fail)} 项 | BLOCKED {len(blocked)} 项 | WARN {len(warn)} 项")
    for title, items in (("FAIL", fail), ("BLOCKED", blocked), ("WARN", warn)):
        for it in items:
            print(f"  {title}: {it}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
