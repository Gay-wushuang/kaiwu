# -*- coding: utf-8 -*-
"""模拟 CIM 后端：用于离线测试任务生命周期，不联网、不消耗配额。

只实现编排层用到的两个方法（solve / get_task_result），返回结构与 SDK 的
“二维 ±1 解矩阵 / 平台结果 dict”保持一致，便于测试归档与恢复逻辑。
"""
from __future__ import annotations

import hashlib
from urllib.error import URLError

import numpy as np


def _seed_from(matrix) -> int:
    h = hashlib.sha256(np.ascontiguousarray(np.asarray(matrix, dtype=np.float64)).tobytes())
    return int(h.hexdigest()[:8], 16)


class MockCIMOptimizer:
    """可注入失败阶段的模拟优化器。

    fail_stage:
        None       正常返回
        "submit"   提交失败（未创建云端任务）
        "run"      提交成功但云端运行失败
        "download" 提交并运行成功，但结果下载失败
        "interrupt" 提交成功后进程被中断（用于测试恢复）
    """

    def __init__(self, task_name: str, wait: bool = True, interval: float = 6,
                 project_no=None, task_mode: str = "optimization",
                 sample_number: int = 10, fail_stage: str = None, seed: int = 2026):
        self.task_name = task_name
        self.wait = wait
        self.interval = interval
        self.project_no = project_no
        self.task_mode = task_mode
        self.sample_number = max(int(sample_number), 10)
        self.fail_stage = fail_stage
        self.seed = seed
        self.submit_count = 0
        self.submitted = False
        self.result_fetches = 0

    # ------------------------------------------------------------------
    def _solutions(self, matrix) -> np.ndarray:
        rng = np.random.default_rng(_seed_from(matrix) ^ self.seed)
        n = int(np.asarray(matrix).shape[0])
        return rng.choice([-1, 1], size=(self.sample_number, n)).astype(np.int8)

    def solve(self, matrix) -> np.ndarray:
        self.submit_count += 1
        if self.fail_stage == "submit":
            raise ValueError("Task creation failed: [mock] 配额不足或提交被拒绝")
        self.submitted = True
        if self.fail_stage == "run":
            raise RuntimeError("Task run failed: [mock] 云端运行失败")
        if self.fail_stage == "download":
            raise URLError("[mock] 结果下载失败：SSL EOF")
        if self.fail_stage == "unknown":
            raise RuntimeError("[mock] 未预期异常（用于验证保守分类）")
        if self.fail_stage == "interrupt":
            raise KeyboardInterrupt("mock: 提交后进程被中断")
        return self._solutions(matrix)

    # ------------------------------------------------------------------
    def get_task_result(self, matrix) -> dict:
        self.result_fetches += 1
        if not self.submitted:
            return {"status": "not_found", "message": "[mock] 没有对应的云端任务"}
        if self.fail_stage == "run":
            return {"status": "failed", "task_status_code": "FAILED",
                    "message": "[mock] 云端运行失败"}
        return {
            "status": "completed",
            "task_status_code": "SUCCESS",
            "task_name": self.task_name,
            "solutions": self._solutions(matrix),
        }
