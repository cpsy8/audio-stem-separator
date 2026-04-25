"""FastAPI app for the local Demucs UI."""
import io
import os
import re
import shutil
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import structlog

from . import logging_config, state as state_mod
from .models import (
    AutorunBody,
    Job,
    JobOptions,
    QueueResponse,
    UploadResponse,
)
from .worker import QueueWorker

log = structlog.get_logger()


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
ALLOWED_EXT = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}

worker: QueueWorker  # set in lifespan


@asynccontextmanager
async def lifespan(_: FastAPI):
    global worker
    logging_config.configure()
    state_mod.ensure_dirs()
    worker = QueueWorker()
    worker.start()
    log.info("server.start")
    yield
    worker.shutdown()
    log.info("server.stop")


app = FastAPI(title="Demucs Local UI", lifespan=lifespan)


def _safe_name(name: str) -> str:
    base = Path(name).name
    return SAFE_NAME_RE.sub("_", base) or "file"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_job(job_id: str) -> Optional[Job]:
    state = state_mod.load_state()
    return next((j for j in state.jobs if j.id == job_id), None)


# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------
@app.get("/api/queue", response_model=QueueResponse)
def get_queue() -> QueueResponse:
    state = state_mod.load_state()
    return QueueResponse(
        autorun=state.autorun,
        current_job_id=worker.current_job_id(),
        autorun_next_at=worker.autorun_next_at_iso(),
        jobs=state.jobs,
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    name: str = Form(...),
    model: str = Form("htdemucs"),
    vocals_only: bool = Form(False),
    wav: bool = Form(False),
    bitrate: int = Form(320),
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(400, "missing filename")
    name = name.strip()
    if not name:
        raise HTTPException(400, "name is required")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"unsupported extension: {ext}")

    job_id = uuid.uuid4().hex
    safe = _safe_name(name) + ext
    dest = state_mod.INPUT_DIR / f"{job_id}__{safe}"
    size = 0
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            size += len(chunk)

    options = JobOptions(
        model=model,  # type: ignore[arg-type]
        vocals_only=vocals_only,
        wav=wav,
        bitrate=bitrate,
    )
    job = Job(
        id=job_id,
        filename=name + ext,
        input_path=f"input/{dest.name}",
        size_bytes=size,
        options=options,
        status="queued",
        queued_at=_now_iso(),
        output_dir=f"output/{job_id}",
    )

    with state_mod.state_lock():
        state = state_mod.load_state()
        state.jobs.append(job)
        state_mod.save_state(state)

    log.info("upload.queued", job_id=job_id, filename=job.filename, size_bytes=size)
    return UploadResponse(job_id=job_id)


@app.delete("/api/queue/{job_id}", status_code=204)
def remove_queued(job_id: str) -> None:
    with state_mod.state_lock():
        state = state_mod.load_state()
        job = next((j for j in state.jobs if j.id == job_id), None)
        if job is None:
            raise HTTPException(404, "job not found")
        if job.status != "queued":
            raise HTTPException(400, f"cannot remove job with status '{job.status}'")
        # delete input file
        in_path = state_mod.REPO_ROOT / job.input_path
        if in_path.exists():
            in_path.unlink(missing_ok=True)
        state.jobs = [j for j in state.jobs if j.id != job_id]
        state_mod.save_state(state)
    log.info("queue.remove", job_id=job_id)


@app.post("/api/run", status_code=204)
def run_now() -> None:
    worker.request_run()


@app.post("/api/stop", status_code=204)
def stop() -> None:
    worker.stop_current()


@app.post("/api/autorun", status_code=204)
def set_autorun(body: AutorunBody) -> None:
    worker.set_autorun(body.enabled)


@app.get("/api/jobs/{job_id}/files")
def list_job_files(job_id: str) -> JSONResponse:
    job = _find_job(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    out_dir = state_mod.REPO_ROOT / job.output_dir
    if not out_dir.exists():
        return JSONResponse([])
    files = []
    for p in out_dir.rglob("*"):
        if p.is_file() and p.name != "_log.txt":
            rel = p.relative_to(out_dir).as_posix()
            files.append({"name": p.name, "path": rel, "size": p.stat().st_size})
    return JSONResponse(files)


@app.get("/api/download/{job_id}/zip")
def download_zip(job_id: str) -> StreamingResponse:
    job = _find_job(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    out_dir = state_mod.REPO_ROOT / job.output_dir
    if not out_dir.exists():
        raise HTTPException(404, "no output for job")

    display = _safe_name(Path(job.filename).stem) or job_id
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in out_dir.rglob("*"):
            if p.is_file() and p.name != "_log.txt":
                stem, ext = os.path.splitext(p.name)
                zf.write(p, f"{display}-{stem}{ext}")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{display}_stems.zip"'},
    )


@app.get("/api/download/{job_id}/file")
def download_file(job_id: str, path: str) -> FileResponse:
    job = _find_job(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    out_dir = (state_mod.REPO_ROOT / job.output_dir).resolve()
    target = (out_dir / path).resolve()
    try:
        target.relative_to(out_dir)
    except ValueError:
        raise HTTPException(400, "invalid path")
    if not target.is_file():
        raise HTTPException(404, "file not found")
    display = _safe_name(Path(job.filename).stem) or job_id
    stem, ext = os.path.splitext(target.name)
    return FileResponse(str(target), filename=f"{display}-{stem}{ext}")


@app.delete("/api/jobs/{job_id}/clear", status_code=204)
def clear_job(job_id: str) -> None:
    with state_mod.state_lock():
        state = state_mod.load_state()
        job = next((j for j in state.jobs if j.id == job_id), None)
        if job is None:
            raise HTTPException(404, "job not found")
        if job.status == "running":
            raise HTTPException(400, "stop the job before clearing")
        in_path = state_mod.REPO_ROOT / job.input_path
        if in_path.exists():
            in_path.unlink(missing_ok=True)
        out_dir = state_mod.REPO_ROOT / job.output_dir
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
        state.jobs = [j for j in state.jobs if j.id != job_id]
        state_mod.save_state(state)
    log.info("job.cleared", job_id=job_id)


# ---------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------
@app.get("/api/logs")
def get_logs_endpoint(since: int = 0) -> list[dict]:
    return logging_config.get_logs(since)


# ---------------------------------------------------------------------
# Static frontend (mount last so /api routes win)
# ---------------------------------------------------------------------
DIST_DIR = state_mod.REPO_ROOT / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="frontend")
else:
    @app.get("/")
    def _no_frontend() -> JSONResponse:
        return JSONResponse(
            {
                "error": "frontend not built",
                "hint": "cd frontend && npm install && npm run build",
            },
            status_code=503,
        )
