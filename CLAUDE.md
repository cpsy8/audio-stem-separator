# music-converter

Demucs stem splitter. CLI wrapper + local web UI (FastAPI + React).

## Stack

- Python 3.11, venv at `venv/`
- Backend: FastAPI + uvicorn, code in `backend/`
- Frontend: React 18 + Vite + TypeScript, code in `frontend/`
- Separation: `separate.py` calls `demucs.separate.main()` via subprocess
- Persistence: `queue.json` (atomic JSON, no DB)

## Run

```powershell
.\run-ui.ps1   # builds frontend if dist missing, activates venv, starts uvicorn
```

Backend only: `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000`
Frontend dev: `cd frontend && npm run dev` (proxies /api → :8000)

## Key files

| File | Purpose |
|------|---------|
| `separate.py` | CLI entry — do not change invocation signature |
| `backend/app.py` | FastAPI routes |
| `backend/worker.py` | QueueWorker thread, subprocess lifecycle |
| `backend/state.py` | Atomic JSON load/save, path constants |
| `backend/models.py` | Pydantic schemas |
| `frontend/src/api.ts` | All API calls |
| `frontend/src/App.tsx` | Poll loop, notification logic |

## Constraints

- One job at a time (CPU-only, laptop hardware)
- Bound to `127.0.0.1` only — no LAN exposure
- `separate.py` unchanged — backend invokes it via subprocess with `--out output/<job_id>`
- `input/`, `output/`, `queue.json`, `frontend/dist/` all gitignored

## Models

`htdemucs` (default) · `htdemucs_ft` · `htdemucs_6s` · `mdx` · `mdx_extra` · `mdx_q` · `mdx_extra_q`

## Output structure

```
output/<job_id>/<model>/<basename>/{vocals,no_vocals,drums,bass,other}.mp3
```
