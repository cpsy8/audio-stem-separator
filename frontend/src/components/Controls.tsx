import { api, QueueResponse } from "../api";

interface Props {
  data: QueueResponse | null;
  onAction: () => void;
}

export default function Controls({ data, onAction }: Props) {
  const running = !!data?.current_job_id;
  const hasQueued = !!data?.jobs.some((j) => j.status === "queued");
  const autorun = !!data?.autorun;
  const nextAt = data?.autorun_next_at
    ? new Date(data.autorun_next_at).toLocaleTimeString()
    : null;

  const onRun = async () => {
    await api.run();
    onAction();
  };
  const onStop = async () => {
    await api.stop();
    onAction();
  };
  const onToggle = async (e: React.ChangeEvent<HTMLInputElement>) => {
    await api.setAutorun(e.target.checked);
    onAction();
  };

  return (
    <div className="controls">
      <button onClick={onRun} disabled={running || !hasQueued}>
        Run next
      </button>
      <button onClick={onStop} disabled={!running} className="danger">
        Stop
      </button>
      <label className="toggle">
        <input type="checkbox" checked={autorun} onChange={onToggle} />
        Auto-run (5 min gap)
      </label>
      {autorun && nextAt && !running && (
        <span className="muted">Next at {nextAt}</span>
      )}
    </div>
  );
}
