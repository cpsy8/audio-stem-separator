# music-converter

A simple CLI wrapper around [Demucs](https://github.com/adefossez/demucs) for separating music into stems (vocals, drums, bass, other) or just removing vocals from a track.

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10 / macOS 11 / Ubuntu 20.04 | Windows 11 / macOS 13 / Ubuntu 22.04 |
| **CPU** | 4-core, 2.0 GHz | 8-core, 3.0 GHz+ |
| **RAM** | 8 GB | 16 GB |
| **Disk space** | 5 GB free | 10 GB free |
| **Python** | 3.10 | 3.11+ |
| **GPU (optional)** | — | NVIDIA GPU with 4 GB VRAM (CUDA 11.8+) |

> **CPU processing time:** A 3–4 minute song takes roughly 3–5 minutes on a modern CPU. A GPU reduces this to under 30 seconds.

> **Disk note:** ~2–3 GB for PyTorch + dependencies, ~80–200 MB per model (downloaded once and cached).

---

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **FFmpeg (full-shared build)** — required for audio decoding on Windows (see setup below)

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/music-converter.git
cd music-converter
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `torch` and `torchaudio` will pull in the CPU-only builds automatically via the `requirements.txt` versions.
> If you want GPU support, install torch manually first from [pytorch.org](https://pytorch.org/get-started/locally/).

### 5. Install FFmpeg (Windows only)

`torchcodec` (used by torchaudio for audio decoding) requires FFmpeg shared DLLs on Windows.

**Option A — Add ffmpeg to your system PATH** (recommended):

1. Download the **full-shared** Windows build from [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds/releases) — look for `ffmpeg-master-latest-win64-gpl-shared.zip`
2. Extract it anywhere, e.g. `C:\ffmpeg\`
3. Add `C:\ffmpeg\bin` to your system `PATH`:
   - Search *"Edit the system environment variables"* in Start
   - Under *System Variables*, edit `Path` and add the `bin` folder

**Option B — Quick PowerShell install into the project folder:**

```powershell
Invoke-WebRequest -Uri "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip" -OutFile "ffmpeg.zip"
Expand-Archive ffmpeg.zip -DestinationPath ffmpeg
Remove-Item ffmpeg.zip
$env:PATH = "$PWD\ffmpeg\ffmpeg-master-latest-win64-gpl-shared\bin;" + $env:PATH
```

> After Option B, the PATH change only lasts for the current PowerShell session. Add the bin path permanently via system settings or add this line to your PowerShell profile.

**macOS / Linux:** Install via your package manager:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

---

## Usage

```
python separate.py <audio_file> [options]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--vocals-only` | off | Two-stem mode: outputs `vocals.mp3` + `no_vocals.mp3` |
| `--model` | `htdemucs` | Model to use (see models below) |
| `--wav` | off | Output as WAV instead of MP3 |
| `--bitrate` | `320` | MP3 bitrate in kbps |
| `--out` | `separated` | Output directory |

### Examples

**Remove vocals (keep instrumental):**
```bash
python separate.py "song.mp3" --vocals-only
```

**Split into all 4 stems (drums, bass, vocals, other):**
```bash
python separate.py "song.mp3"
```

**Use a higher-quality fine-tuned model:**
```bash
python separate.py "song.mp3" --vocals-only --model htdemucs_ft
```

**Output as WAV:**
```bash
python separate.py "song.mp3" --vocals-only --wav
```

**Custom output directory:**
```bash
python separate.py "song.mp3" --vocals-only --out my_output
```

---

## Output structure

```
separated/
  htdemucs/
    song_name/
      no_vocals.mp3   ← instrumental (vocals removed)
      vocals.mp3      ← isolated vocals
```

In full 4-stem mode:
```
separated/
  htdemucs/
    song_name/
      drums.mp3
      bass.mp3
      vocals.mp3
      other.mp3
```

---

## Available models

| Model | Description |
|-------|-------------|
| `htdemucs` | Default. Fast and good quality (Hybrid Transformer) |
| `htdemucs_ft` | Fine-tuned version of htdemucs — better quality, slower |
| `htdemucs_6s` | 6-stem model: adds piano + guitar stems |
| `mdx` | MDX-Net model |
| `mdx_extra` | MDX-Net with extra training data |
| `mdx_q` | Quantized MDX-Net (faster, slightly lower quality) |
| `mdx_extra_q` | Quantized MDX-Net extra |

> Models are downloaded automatically on first use (~80–200 MB each) and cached in `~/.cache/torch/hub/`.

---

## Notes

- All processing runs on **CPU** by default. For GPU inference, remove `-d cpu` from `separate.py`.
- First run downloads the model weights — subsequent runs are faster.
- Supported input formats: MP3, WAV, FLAC, M4A, OGG, and anything FFmpeg can decode.

---

## Local Web UI

A local-only browser UI (FastAPI + React) that wraps `separate.py` with a queue, progress, and download UI. Bound to `127.0.0.1` — only your machine can reach it.

### Extra prerequisites

- **Node.js 18+** (one-time, for building the frontend)

### One-time install

```bash
pip install -r requirements.txt          # adds fastapi, uvicorn, python-multipart
cd frontend
npm install
npm run build
cd ..
```

### Run

**Windows (PowerShell):**
```powershell
.\run-ui.ps1
```

**macOS / Linux:**
```bash
./run-ui.sh
```

Then open <http://127.0.0.1:8000>.

### What the UI does

- Upload audio file (mp3/wav/flac/m4a/ogg/aac) → stored in `input/`
- Per-file options (model, vocals-only, format, bitrate)
- FIFO queue, **one job at a time** (CPU-friendly)
- **Run next** button or **Auto-run** (next job 5 min after the previous finishes)
- **Stop** to kill the running job (partial output purged)
- Live progress bar (size + history-based estimate, no extra CPU)
- Browser notification on completion
- Download zip of all stems or individual files
- **Clear** removes the input file + output folder for a job
- **Remove** removes a queued (not-yet-started) job from the queue
- Queue + history persisted in `queue.json` — survives restarts

### Folders

| Path | Purpose |
|------|---------|
| `input/` | Uploaded files (gitignored) |
| `output/<job_id>/` | Per-job stem output (gitignored) |
| `queue.json` | Queue + run-time history (gitignored) |
| `frontend/dist/` | Built UI served by FastAPI (gitignored) |
