import { useEffect, useRef, useState } from "react";
import { api, QueueResponse } from "./api";
import UploadForm from "./components/UploadForm";
import QueueTable from "./components/QueueTable";
import StatusBar from "./components/StatusBar";
import Controls from "./components/Controls";

const POLL_MS = 2000;

export default function App() {
  const [data, setData] = useState<QueueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const prevStatuses = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const q = await api.getQueue();
        if (cancelled) return;
        // detect running -> completed transitions for notifications
        for (const job of q.jobs) {
          const prev = prevStatuses.current.get(job.id);
          if (prev === "running" && job.status === "completed") {
            notify(`Done: ${job.filename}`);
          } else if (prev === "running" && job.status === "failed") {
            notify(`Failed: ${job.filename}`);
          }
          prevStatuses.current.set(job.id, job.status);
        }
        setData(q);
        setError(null);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    };
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const refresh = () => api.getQueue().then(setData).catch(() => {});

  return (
    <div className="app">
      <header>
        <h1>Demucs Local UI</h1>
      </header>

      <StatusBar data={data} />

      <section className="card">
        <h2>Upload</h2>
        <UploadForm onUploaded={refresh} />
      </section>

      <section className="card">
        <Controls data={data} onAction={refresh} />
      </section>

      <section className="card">
        <h2>Queue</h2>
        {error && <div className="error">API error: {error}</div>}
        <QueueTable data={data} onAction={refresh} />
      </section>
    </div>
  );
}

function notify(text: string) {
  if (!("Notification" in window)) return;
  if (Notification.permission === "granted") {
    try {
      new Notification(text);
    } catch {
      /* ignore */
    }
  }
}
