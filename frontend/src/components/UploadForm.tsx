import { useState } from "react";
import { api, ModelName } from "../api";

const MODELS: ModelName[] = [
  "htdemucs",
  "htdemucs_ft",
  "htdemucs_6s",
  "mdx",
  "mdx_extra",
  "mdx_q",
  "mdx_extra_q",
];

interface Props {
  onUploaded: () => void;
}

export default function UploadForm({ onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState<ModelName>("htdemucs");
  const [vocalsOnly, setVocalsOnly] = useState(false);
  const [wav, setWav] = useState(false);
  const [bitrate, setBitrate] = useState(320);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setErr(null);
    try {
      await api.upload(file, { model, vocals_only: vocalsOnly, wav, bitrate });
      setFile(null);
      (e.target as HTMLFormElement).reset();
      onUploaded();
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="upload-form" onSubmit={submit}>
      <div className="row">
        <label>
          File
          <input
            type="file"
            accept=".mp3,.wav,.flac,.m4a,.ogg,.aac"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
        </label>
      </div>

      <div className="row">
        <label>
          Model
          <select value={model} onChange={(e) => setModel(e.target.value as ModelName)}>
            {MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>

        <label>
          Bitrate (kbps)
          <input
            type="number"
            min={64}
            max={320}
            step={32}
            value={bitrate}
            onChange={(e) => setBitrate(Number(e.target.value))}
            disabled={wav}
          />
        </label>
      </div>

      <div className="row checkboxes">
        <label>
          <input
            type="checkbox"
            checked={vocalsOnly}
            onChange={(e) => setVocalsOnly(e.target.checked)}
          />
          Vocals-only (2-stem)
        </label>
        <label>
          <input
            type="checkbox"
            checked={wav}
            onChange={(e) => setWav(e.target.checked)}
          />
          Output WAV
        </label>
      </div>

      <div className="row">
        <button type="submit" disabled={busy || !file}>
          {busy ? "Uploading..." : "Add to queue"}
        </button>
        {err && <span className="error">{err}</span>}
      </div>
    </form>
  );
}
