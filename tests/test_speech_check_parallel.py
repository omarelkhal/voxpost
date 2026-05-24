"""Tests for speech-check process-pool chunking."""

import os

from voxpost.speech_check_parallel import (
    WorkerJob,
    apply_worker_cpu_threads,
    merge_round_robin,
    recommended_workers,
    resolve_workers,
    split_round_robin,
)


def test_split_merge_round_robin_preserves_order():
    items = list(range(24))
    buckets = split_round_robin(items, workers=4)
    assert sum(len(b) for b in buckets) == 24
    restored = merge_round_robin(buckets)
    assert restored == items


def test_resolve_workers_clamps_to_cases_and_cores():
    assert resolve_workers(8, case_count=3) == 3
    assert resolve_workers(1, case_count=24) == 1


def test_recommended_workers_on_multi_core():
    count = recommended_workers(case_count=24)
    assert count >= 2


def test_apply_worker_cpu_threads_sets_env(monkeypatch):
    monkeypatch.delenv("VOXPOST_SUMMARIZER_CPU_THREADS", raising=False)
    job = WorkerJob(
        config_dir=None,
        local_files_only=False,
        model=None,
        effective_workers=4,
    )
    apply_worker_cpu_threads(job)
    assert os.environ.get("VOXPOST_SUMMARIZER_CPU_THREADS") is not None
