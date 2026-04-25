import { useEffect, useState } from "react";
import { QueueResponse } from "../api";

interface Props {
  data: QueueResponse | null;
}

export default function StatusBar({ data }: Props) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), 500);
    return () => clearInterval(id);
  }, []);

  if (!data) return <div className="statusbar muted">Loading...</div>;
  const cur = data.jobs.find((j) => j.id === data.current_job_id);
  if (!cur) {
    return <div className="statusbar muted">Idle</div>;
  }
  const pct = computePercent(cur.started_at, cur.estimated_duration_sec);
  return (
    <div className="statusbar">
      <div className="statusbar-text">
        <strong>{cur.filename}</strong>
        <span> — {Math.floor(pct)}%</span>
      </div>
      <div className="bar">
        <div className="bar-fill" style={{ width: `${pct.toFixed(2)}%` }} />
      </div>
    </div>
  );
}

function computePercent(startedAt: string | null, est: number): number {
  if (!startedAt || est <= 0) return 0;
  const elapsed = (Date.now() - new Date(startedAt).getTime()) / 1000;
  return Math.min(99, (elapsed / est) * 100);
}
