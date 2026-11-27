# -*- coding: utf-8 -*-
"""本地配额预算检查（Phase 10）。

SDK 不提供配额查询接口，因此这里只做“本地账本”：
- 预算总额由用户提供并写入 experiments/config/quota_budget.json；
- 已消耗量按本地任务注册表保守累计（只有确认任务已创建才计数）；
- 该检查不能替代平台真实余额，任何提交前仍需人工核对。
"""
from __future__ import annotations

import json
from pathlib import Path

from experiment_archive import Registry, now_str
from experiment_input import config_root

SCHEMA_VERSION = 1

MODES = {
    "optimization": {"key": "optimization", "label": "优化任务（OPTIMIZATION）"},
    "opt": {"key": "optimization", "label": "优化任务（OPTIMIZATION）"},
    "sampling": {"key": "sampling", "label": "采样任务（SAMPLING）"},
}

DEFAULT_BUDGET = {
    "schema_version": SCHEMA_VERSION,
    "updated_at": None,
    "source": "用户口述 2026-11-27，未经平台核对",
    "verified": False,
    "budgets": {
        "optimization": {"total": 32, "note": "SPQC-550 31 次 + SPQC-1000 1 次"},
        "sampling": {"total": 0, "note": "采样配额为 0"},
    },
}


def budget_path() -> Path:
    return config_root() / "quota_budget.json"


def ensure_budget() -> Path:
    """首次运行时写入模板；之后的修改完全由用户负责，工具不自动改数。"""
    p = budget_path()
    if not p.is_file():
        p.parent.mkdir(parents=True, exist_ok=True)
        data = dict(DEFAULT_BUDGET)
        data["updated_at"] = now_str()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def read_budget() -> dict:
    p = ensure_budget()
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"[配额] 预算文件版本不支持：{p}")
    return data


def mode_key(mode: str) -> str:
    if mode not in MODES:
        raise SystemExit(f"[配额] 未知模式 {mode}，只支持 optimization / sampling")
    return MODES[mode]["key"]


def available(mode: str, registry: Registry = None) -> dict:
    reg = registry or Registry()
    key = mode_key(mode)
    data = read_budget()
    total = int(data["budgets"].get(key, {}).get("total", 0))
    used = reg.quota_consumed(key)
    return {
        "mode": key,
        "label": MODES[key]["label"],
        "total": total,
        "used": used,
        "remaining": total - used,
        "verified": bool(data.get("verified", False)),
        "source": data.get("source"),
    }


def check(mode: str, units: int = 1, registry: Registry = None) -> dict:
    """提交前检查预算；不足时直接中止，不进入任何网络路径。"""
    info = available(mode, registry)
    if info["remaining"] < units:
        raise SystemExit(
            f"[配额] 本地预算不足：{info['label']} 总额 {info['total']}，已用 {info['used']}，"
            f"剩余 {info['remaining']}，本次需要 {units}。\n"
            f"预算来源：{info['source']}（verified={info['verified']}）。\n"
            "请先在平台核实余额，再修改 experiments/config/quota_budget.json。"
        )
    return info
