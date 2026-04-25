"""Single-job FIFO queue worker.

One subprocess at a time. Manual run via request_run(); autorun fires the
next job 5 minutes after the previous job ends (success, fail, or cancel).
"""
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import state as state_mod
from .models import HistoryEntry, Job, QueueState

AUTORUN_DELAY_SEC = 300
DEFAULT_SEC_PER_MB = 60.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class QueueWorker:
    def __init__(self) -> None:
        self._lock = state_mod.state_lock()
        self._wake = threading.Event()
        self._stop_flag = threading.Event()
        self._current_proc: Optional[subprocess.Popen] = None
        self._current_job_id: Optional[str] = None
        self._cancelled_ids: set[str] = set()
        self._autorun_timer: Optional[threading.Timer] = None
        self._autorun_next_at: Optional[datetime] = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    # -- lifecycle ----------------------------------------------------
    def start(self) -> None:
        self._thread.start()

    def shutdown(self) -> None:
        self._stop_flag.set()
        self._cancel_autorun_timer()
        self.stop_current()
        self._wake.set()

    # -- public api ---------------------------------------------------
    def request_run(self) -> None:
        """Manually trigger next job. Cancels any pending autorun timer."""
        self._cancel_autorun_timer()
        self._wake.set()

    def stop_current(self) -> None:
        """Kill running subprocess (if any) and mark its job cancelled."""
        with self._lock:
            proc = self._current_proc
            job_id = self._current_job_id
        if proc is None or job_id is None:
            return
        self._cancelled_ids.add(job_id)
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:
            pass

    def set_autorun(self, enabled: bool) -> None:
        with self._lock:
            state = state_mod.load_state()
            state.autorun = enabled
            state_mod.save_state(state)
        if not enabled:
            self._cancel_autorun_timer()
        else:
            # if idle and there is queued work, start the 5-min timer
            with self._lock:
                state = state_mod.load_state()
                idle = self._current_proc is None
                has_queued = any(j.status == "queued" for j in state.jobs)
            if idle and has_queued and self._autorun_timer is None:
                self._schedule_autorun()

    def current_job_id(self) -> Optional[str]:
        with self._lock:
            return self._current_job_id

    def autorun_next_at_iso(self) -> Optional[str]:
        if self._autorun_next_at is None:
            return None
        return self._autorun_next_at.isoformat()

    # -- internals ----------------------------------------------------
    def _cancel_autorun_timer(self) -> None:
        if self._autorun_timer is not None:
            self._autorun_timer.cancel()
            self._autorun_timer = None
            self._autorun_next_at = None

    def _schedule_autorun(self) -> None:
        self._cancel_autorun_timer()
        self._autorun_next_at = datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta
        self._autorun_next_at = self._autorun_next_at + timedelta(seconds=AUTORUN_DELAY_SEC)
        t = threading.Timer(AUTORUN_DELAY_SEC, self._autorun_fire)
        t.daemon = True
        self._autorun_timer = t
        t.start()

    def _autorun_fire(self) -> None:
        self._autorun_timer = None
        self._autorun_next_at = None
        self._wake.set()

    def _pick_next(self) -> Optional[Job]:
        with self._lock:
            state = state_mod.load_state()
            for job in state.jobs:
                if job.status == "queued":
                    return job
            return None

    def _estimate(self, state: QueueState, job: Job) -> float:
        size_mb = max(0.1, job.size_bytes / (1024 * 1024))
        entry = state.history.get(job.options.model)
        rate = entry.sec_per_mb if entry and entry.samples > 0 else DEFAULT_SEC_PER_MB
        return round(size_mb * rate, 1)

    def _record_history(self, job: Job, elapsed_sec: float) -> None:
        size_mb = max(0.1, job.size_bytes / (1024 * 1024))
        sec_per_mb = elapsed_sec / size_mb
        with self._lock:
            state = state_mod.load_state()
            entry = state.history.get(job.options.model)
            if entry is None or entry.samples <= 0:
                state.history[job.options.model] = HistoryEntry(
                    sec_per_mb=sec_per_mb, samples=1
                )
            else:
                # rolling avg, cap weight so old runs still influence
                samples = min(entry.samples, 9) + 1
                avg = (entry.sec_per_mb * (samples - 1) + sec_per_mb) / samples
                state.history[job.options.model] = HistoryEntry(
                    sec_per_mb=avg, samples=samples
                )
            state_mod.save_state(state)

    def _build_cmd(self, job: Job) -> list[str]:
        cmd = [
            sys.executable,
            "separate.py",
            job.input_path,
            "--model", job.options.model,
            "--out", job.output_dir,
            "--bitrate", str(job.options.bitrate),
        ]
        if job.options.wav:
            cmd.append("--wav")
        if job.options.vocals_only:
            cmd.append("--vocals-only")
        return cmd

    def _process(self, job: Job) -> None:
        out_dir = state_mod.REPO_ROOT / job.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        with self._lock:
            state = state_mod.load_state()
            j = next((x for x in state.jobs if x.id == job.id), None)
            if j is None:
                return
            j.status = "running"
            j.started_at = _now_iso()
            j.estimated_duration_sec = self._estimate(state, j)
            state_mod.save_state(state)
            job = j  # use refreshed copy

        log_path = out_dir / "_log.txt"
        cmd = self._build_cmd(job)
        start_ts = datetime.now(timezone.utc)
        rc: int
        with open(log_path, "wb") as logf:
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(state_mod.REPO_ROOT),
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                )
            except Exception as exc:
                self._finish(job, "failed", error=str(exc))
                return

            with self._lock:
                self._current_proc = proc
                self._current_job_id = job.id

            rc = proc.wait()

            with self._lock:
                self._current_proc = None
                self._current_job_id = None

        elapsed = (datetime.now(timezone.utc) - start_ts).total_seconds()

        if job.id in self._cancelled_ids:
            self._cancelled_ids.discard(job.id)
            self._purge_output(job)
            self._finish(job, "cancelled")
        elif rc != 0:
            self._finish(job, "failed", error=f"separate.py exit {rc} (see {log_path.name})")
        else:
            self._record_history(job, elapsed)
            self._finish(job, "completed")

    def _purge_output(self, job: Job) -> None:
        out_dir = state_mod.REPO_ROOT / job.output_dir
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)

    def _finish(self, job: Job, status: str, error: Optional[str] = None) -> None:
        with self._lock:
            state = state_mod.load_state()
            j = next((x for x in state.jobs if x.id == job.id), None)
            if j is not None:
                j.status = status  # type: ignore[assignment]
                j.completed_at = _now_iso()
                if error:
                    j.error = error
                state_mod.save_state(state)
            autorun = state.autorun if j is not None else False
            has_more = any(x.status == "queued" for x in state.jobs)
        if autorun and has_more:
            self._schedule_autorun()

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            self._wake.wait()
            self._wake.clear()
            if self._stop_flag.is_set():
                return
            while True:
                job = self._pick_next()
                if job is None:
                    break
                self._process(job)
                # only auto-chain when autorun is on; manual mode = one per click
                with self._lock:
                    state = state_mod.load_state()
                    autorun = state.autorun
                if not autorun:
                    break
                # autorun path: schedule next via timer, do not loop now
                break
