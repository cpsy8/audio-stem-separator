from typing import Literal, Optional
from pydantic import BaseModel, Field


ModelName = Literal[
    "htdemucs", "htdemucs_ft", "htdemucs_6s",
    "mdx", "mdx_extra", "mdx_q", "mdx_extra_q",
]
JobStatus = Literal["queued", "running", "completed", "cancelled", "failed"]


class JobOptions(BaseModel):
    model: ModelName = "htdemucs"
    vocals_only: bool = False
    wav: bool = False
    bitrate: int = 320


class Job(BaseModel):
    id: str
    filename: str
    input_path: str
    size_bytes: int
    options: JobOptions
    status: JobStatus = "queued"
    queued_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_duration_sec: float = 0.0
    output_dir: str
    error: Optional[str] = None


class HistoryEntry(BaseModel):
    sec_per_mb: float
    samples: int = 0


class QueueState(BaseModel):
    autorun: bool = False
    history: dict[str, HistoryEntry] = Field(default_factory=dict)
    jobs: list[Job] = Field(default_factory=list)


class AutorunBody(BaseModel):
    enabled: bool


class UploadResponse(BaseModel):
    job_id: str


class QueueResponse(BaseModel):
    autorun: bool
    current_job_id: Optional[str]
    autorun_next_at: Optional[str] = None
    jobs: list[Job]
