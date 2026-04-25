import { useEffect, useState } from "react";
import { api, Job, JobFile, QueueResponse } from "../api";

interface Props {
  data: QueueResponse | null;
  onAction: () => void;
}

export default function QueueTable({ data, onAction }: Props) {
  if (!data) return null;
  if (data.jobs.length === 0) {
    return <div className="muted">Empty queue</div>;
  }
  return (
    <table className="queue">
      <thead>
        <tr>
          <th>#</th>
          <th>File</th>
          <th>Size</th>
          <th>Options</th>
          <th>Status</th>
          <th>Progress</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {data.jobs.map((job, i) => (
          <Row key={job.id} job={job} idx={i + 1} onAction={onAction} />
        ))}
      </tbody>
    </table>
  );
}

function Row({
  job,
  idx,
  onAction,
}: {
  job: Job;
  idx: number;
  onAction: () => void;
}) {
  const [, setTick] = useState(0);
  const [files, setFiles] = useState<JobFile[] | null>(null);
  const [showFiles, setShowFiles] = useState(false);

  useEffect(() => {
    if (job.status !== "running") return;
    const id = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [job.status]);

  useEffect(() => {
    if (!showFiles || files !== null) return;
    api.listFiles(job.id).then(setFiles).catch(() => setFiles([]));
  }, [showFiles, files, job.id]);

  const pct =
    job.status === "running"
      ? computePercent(job.started_at, job.estimated_duration_sec)
      : job.status === "completed"
      ? 100
      : 0;

  const onRemove = async () => {
    if (!confirm(`Remove "${job.filename}" from queue?`)) return;
    await api.remove(job.id);
    onAction();
  };
  const onClear = async () => {
    if (!confirm(`Delete input + outputs for "${job.filename}"?`)) return;
    await api.clear(job.id);
    onAction();
  };

  return (
    <>
      <tr>
        <td>{idx}</td>
        <td className="filename" title={job.filename}>{job.filename}</td>
        <td>{formatSize(job.size_bytes)}</td>
        <td className="opts">{summarizeOpts(job)}</td>
        <td>
          <span className={`status status-${job.status}`}>{job.status}</span>
          {job.error && <div className="error small">{job.error}</div>}
        </td>
        <td className="progress-cell">
          <div className="bar small">
            <div className="bar-fill" style={{ width: `${pct}%` }} />
          </div>
          <span className="pct">{pct}%</span>
        </td>
        <td className="actions">
          {job.status === "queued" && (
            <button onClick={onRemove}>Remove</button>
          )}
          {job.status === "completed" && (
            <>
              <a
                className="btn"
                href={api.zipUrl(job.id)}
                download
              >
                Zip
              </a>
              <button onClick={() => setShowFiles((v) => !v)}>
                {showFiles ? "Hide files" : "Files"}
              </button>
              <button onClick={onClear} className="danger">Clear</button>
            </>
          )}
          {(job.status === "failed" || job.status === "cancelled") && (
            <button onClick={onClear} className="danger">Clear</button>
          )}
        </td>
      </tr>
      {showFiles && files && (
        <tr className="files-row">
          <td colSpan={7}>
            {files.length === 0 ? (
              <span className="muted">No output files</span>
            ) : (
              <ul className="files">
                {files.map((f) => (
                  <li key={f.path}>
                    <a href={api.fileUrl(job.id, f.path)} download>{f.path}</a>
                    <span className="muted"> ({formatSize(f.size)})</span>
                  </li>
                ))}
              </ul>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function summarizeOpts(job: Job): string {
  const o = job.options;
  const parts: string[] = [o.model];
  if (o.vocals_only) parts.push("vocals-only");
  parts.push(o.wav ? "wav" : `mp3@${o.bitrate}`);
  return parts.join(" / ");
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function computePercent(startedAt: string | null, est: number): number {
  if (!startedAt || est <= 0) return 0;
  const start = new Date(startedAt).getTime();
  const elapsed = (Date.now() - start) / 1000;
  return Math.max(0, Math.min(99, Math.round((elapsed / est) * 100)));
}
