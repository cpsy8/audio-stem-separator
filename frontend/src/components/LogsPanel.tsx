import { useEffect, useRef, useState } from "react";
import { api, LogEntry } from "../api";

const POLL_MS = 2000;

export default function LogsPanel() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [open, setOpen] = useState(false);
  const lastSeq = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const fresh = await api.getLogs(lastSeq.current);
        if (cancelled || fresh.length === 0) return;
        lastSeq.current = fresh[fresh.length - 1].seq;
        setEntries((prev) => [...prev.slice(-500), ...fresh]);
      } catch {
        /* ignore fetch errors */
      }
    };
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    if (open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries, open]);

  const SKIP = new Set(["seq", "timestamp", "level", "event"]);

  return (
    <section className="card logs-panel">
      <div className="logs-header" onClick={() => setOpen((o) => !o)}>
        <h2>
          Logs
          {entries.length > 0 && (
            <span className="log-count">{entries.length}</span>
          )}
        </h2>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {entries.length > 0 && (
            <button
              className="btn-ghost"
              onClick={(e) => {
                e.stopPropagation();
                setEntries([]);
                lastSeq.current = 0;
              }}
            >
              Clear
            </button>
          )}
          <span className="logs-toggle">{open ? "▲" : "▼"}</span>
        </div>
      </div>

      {open && (
        <div className="logs-body" ref={scrollRef}>
          {entries.length === 0 ? (
            <span className="muted">No logs yet.</span>
          ) : (
            entries.map((e) => (
              <div key={e.seq} className="log-line">
                <span className="log-ts">
                  {String(e.timestamp ?? "").slice(11, 19)}
                </span>
                <span className={`log-level level-${e.level}`}>
                  {String(e.level ?? "").toUpperCase()}
                </span>
                <span className="log-event">{String(e.event ?? "")}</span>
                {Object.entries(e)
                  .filter(([k]) => !SKIP.has(k))
                  .map(([k, v]) => (
                    <span key={k} className="log-kv">
                      <span className="log-key">{k}=</span>
                      <span className="log-val">{String(v)}</span>
                    </span>
                  ))}
              </div>
            ))
          )}
        </div>
      )}
    </section>
  );
}
