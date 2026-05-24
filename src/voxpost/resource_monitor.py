"""Measure CPU and RAM for a running Voxpost Python process."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")

_MB = 1024 * 1024
_SAMPLE_INTERVAL_S = 0.1


@dataclass(frozen=True)
class ResourceSnapshot:
    """Point-in-time process memory (RSS + peak HWM when available)."""

    rss_mb: float
    peak_rss_mb: float


@dataclass(frozen=True)
class ResourceUsage:
    """Resource delta for one timed operation."""

    label: str
    wall_seconds: float
    rss_before_mb: float
    rss_after_mb: float
    rss_delta_mb: float
    peak_rss_mb: float
    cpu_percent_avg: float


def _read_proc_rss_mb(pid: int) -> tuple[float, float]:
    """Return (rss_mb, hwm_mb) from /proc on Linux; fallback to rss only."""
    status_path = f"/proc/{pid}/status"
    rss_kb = 0.0
    hwm_kb = 0.0
    try:
        with open(status_path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    rss_kb = float(line.split()[1])
                elif line.startswith("VmHWM:"):
                    hwm_kb = float(line.split()[1])
    except OSError:
        pass
    rss_mb = rss_kb / 1024 if rss_kb else 0.0
    peak_mb = hwm_kb / 1024 if hwm_kb else rss_mb
    return rss_mb, peak_mb


def current_snapshot(pid: int | None = None) -> ResourceSnapshot:
    """Current RSS for this process (or pid). Uses psutil when installed."""
    pid = pid or os.getpid()
    try:
        import psutil

        proc = psutil.Process(pid)
        mem = proc.memory_info()
        rss_mb = mem.rss / _MB
        peak_mb = getattr(mem, "peak_wss", None)
        if peak_mb is None:
            peak_mb = mem.rss
        return ResourceSnapshot(rss_mb=rss_mb, peak_rss_mb=peak_mb / _MB)
    except ImportError:
        rss_mb, peak_mb = _read_proc_rss_mb(pid)
        return ResourceSnapshot(rss_mb=rss_mb, peak_rss_mb=peak_mb)


def measure_operation(label: str, fn: Callable[[], T], *, pid: int | None = None) -> tuple[T, ResourceUsage]:
    """
    Run fn while sampling RSS peak and average CPU.

    CPU average uses psutil when available; otherwise reports 0.
    """
    pid = pid or os.getpid()
    before = current_snapshot(pid)
    peak_rss = before.rss_mb
    cpu_samples: list[float] = []
    stop = threading.Event()

    def _poll() -> None:
        nonlocal peak_rss
        proc = None
        try:
            import psutil

            proc = psutil.Process(pid)
            proc.cpu_percent(None)
        except ImportError:
            proc = None
        while not stop.wait(_SAMPLE_INTERVAL_S):
            snap = current_snapshot(pid)
            peak_rss = max(peak_rss, snap.rss_mb, snap.peak_rss_mb)
            if proc is not None:
                try:
                    cpu_samples.append(proc.cpu_percent(None))
                except Exception:  # noqa: BLE001
                    break

    sampler = threading.Thread(target=_poll, name="voxpost-resource-poll", daemon=True)
    started = time.perf_counter()
    sampler.start()
    try:
        result = fn()
    finally:
        stop.set()
        sampler.join(timeout=2.0)
    wall = time.perf_counter() - started
    after = current_snapshot(pid)
    peak_rss = max(peak_rss, after.rss_mb, after.peak_rss_mb)
    cpu_avg = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0

    usage = ResourceUsage(
        label=label,
        wall_seconds=wall,
        rss_before_mb=before.rss_mb,
        rss_after_mb=after.rss_mb,
        rss_delta_mb=after.rss_mb - before.rss_mb,
        peak_rss_mb=peak_rss,
        cpu_percent_avg=cpu_avg,
    )
    return result, usage
