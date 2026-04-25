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

const MODEL_INFO: Record<ModelName, string> = {
  htdemucs:      "4-stem (vocals / drums / bass / other) · fast · default",
  htdemucs_ft:   "Fine-tuned htdemucs · better quality · ~2× slower",
  htdemucs_6s:   "6-stem: adds guitar + piano · longest runtime",
  mdx:           "MDX-Net 4-stem · different architecture, good quality",
  mdx_extra:     "MDX-Net extra quality · slower than mdx",
  mdx_q:         "MDX-Net quantized · faster, slightly lower quality",
  mdx_extra_q:   "MDX-Net extra quantized · balanced quality / speed",
};

interface Props {
  onUploaded: () => void;
}

export default function UploadForm({ onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [model, setModel] = useState<ModelName>("htdemucs");
  const [vocalsOnly, setVocalsOnly] = useState(false);
  const [wav, setWav] = useState(false);
  const [bitrate, setBitrate] = useState(320);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !name.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      await api.upload(file, name.trim(), { model, vocals_only: vocalsOnly, wav, bitrate });
      setFile(null);
      setName("");
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
        <label>
          Name
          <input
            type="text"
            placeholder="e.g. Khumaar Live"
            value={name}
            onChange={(e) => setName(e.target.value)}
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
          <span className="help-text">{MODEL_INFO[model]}</span>
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
          <span className="help-text">
            {wav ? "N/A — WAV output selected" : "MP3 quality: 320 = highest, 64 = smallest"}
          </span>
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
          <span className="help-text">Outputs vocals + accompaniment only — skips drums/bass/other. Faster.</span>
        </label>
        <label>
          <input
            type="checkbox"
            checked={wav}
            onChange={(e) => setWav(e.target.checked)}
          />
          Output WAV
          <span className="help-text">Lossless WAV instead of MP3. Larger files, no encoding loss.</span>
        </label>
      </div>

      <div className="row">
        <button type="submit" disabled={busy || !file || !name.trim()}>
          {busy ? "Uploading..." : "Add to queue"}
        </button>
        {err && <span className="error">{err}</span>}
      </div>
    </form>
  );
}
