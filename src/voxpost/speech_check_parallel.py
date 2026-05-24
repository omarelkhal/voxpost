"""Process-pool helpers for parallel speech-check runs."""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")

# Rough warm RSS per chat-LM worker (Qwen3.5-0.8B on CPU) for CLI warnings.
_ESTIMATED_WORKER_RSS_MB = 2100


@dataclass(frozen=True)
class WorkerJob:
    config_dir: str | None
    local_files_only: bool
    model: str | None
    effective_workers: int = 1
    speakable_lang: str | None = None


def apply_worker_cpu_threads(job: WorkerJob) -> None:
    """
    When multiple processes run inference, give each a fair share of CPU threads.

    Avoids N workers each grabbing half of all cores (torch oversubscription).
    """
    if job.effective_workers <= 1:
        return
    cores = os.cpu_count() or 4
    per_worker = max(1, cores // job.effective_workers)
    os.environ["VOXPOST_SUMMARIZER_CPU_THREADS"] = str(per_worker)


def recommended_workers(*, case_count: int) -> int:
    """Heuristic max useful workers for this machine and case count."""
    cores = os.cpu_count() or 4
    # CPU inference: beyond ~cores/2 yields diminishing returns for small models.
    cap = max(2, min(cores, cores // 2 + 2))
    return resolve_workers(cap, case_count=case_count)


def resolve_workers(requested: int, *, case_count: int) -> int:
    """Clamp worker count to cases and CPU cores."""
    if requested <= 1 or case_count <= 1:
        return 1
    cores = os.cpu_count() or 2
    return max(1, min(requested, case_count, cores))


def estimated_worker_ram_mb(workers: int) -> int:
    return _ESTIMATED_WORKER_RSS_MB * workers


def split_round_robin(cases: Sequence[T], workers: int) -> list[list[T]]:
    """Split cases across workers; worker 0 gets 0, N, 2N… preserves merge order."""
    n = resolve_workers(workers, case_count=len(cases))
    buckets: list[list[T]] = [[] for _ in range(n)]
    for index, case in enumerate(cases):
        buckets[index % n].append(case)
    return buckets


def merge_round_robin(chunks: Sequence[Sequence[R]]) -> list[R]:
    """Interleave chunk results back into original case order."""
    if not chunks:
        return []
    merged: list[R] = []
    max_len = max(len(chunk) for chunk in chunks)
    for index in range(max_len):
        for chunk in chunks:
            if index < len(chunk):
                merged.append(chunk[index])
    return merged


def run_in_process_pool(
    cases: Sequence[T],
    workers: int,
    worker_fn: Callable[[list[T], WorkerJob], list[R]],
    job: WorkerJob,
) -> list[R]:
    """Run worker_fn on case chunks; one model load per worker process."""
    buckets = split_round_robin(cases, workers)
    if len(buckets) <= 1:
        return worker_fn(list(cases), job)

    chunk_results: list[list[R] | None] = [None] * len(buckets)
    with ProcessPoolExecutor(max_workers=len(buckets)) as pool:
        futures = {
            pool.submit(worker_fn, bucket, job): index
            for index, bucket in enumerate(buckets)
        }
        for future in as_completed(futures):
            chunk_results[futures[future]] = future.result()
    return merge_round_robin([chunk for chunk in chunk_results if chunk is not None])


def worker_job_from_config(
    *,
    config_dir: Path | None,
    local_files_only: bool,
    model: str | None,
) -> WorkerJob:
    return WorkerJob(
        config_dir=str(config_dir) if config_dir is not None else None,
        local_files_only=local_files_only,
        model=model,
    )


def config_dir_from_job(job: WorkerJob) -> Path | None:
    return Path(job.config_dir) if job.config_dir else None
