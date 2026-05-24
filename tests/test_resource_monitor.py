"""Tests for process resource monitoring helpers."""

from __future__ import annotations

import time

from voxpost.resource_monitor import current_snapshot, measure_operation


def test_current_snapshot_returns_positive_rss():
    snap = current_snapshot()
    assert snap.rss_mb > 0
    assert snap.peak_rss_mb >= snap.rss_mb


def test_measure_operation_captures_wall_time():
    def work() -> int:
        time.sleep(0.05)
        return 42

    value, usage = measure_operation("sleep", work)
    assert value == 42
    assert usage.wall_seconds >= 0.04
    assert usage.label == "sleep"
    assert usage.peak_rss_mb >= usage.rss_before_mb
