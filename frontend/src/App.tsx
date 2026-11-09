import { useCallback, useEffect, useRef, useState } from "react";
import { getSources, setSource, setTracking, StreamClient, updateSettings } from "./api";
import { ControlDeck, type FramingPreset } from "./components/ControlDeck";
import { OutputPanel } from "./components/OutputPanel";
import { PreviewCanvas } from "./components/PreviewCanvas";
import { SettingsModal, type TuningValues } from "./components/SettingsModal";
import { SourceList, sourceKey } from "./components/SourceList";
import type { FrameMetadata, SourceInfo, StatusDto } from "./types";

export default function App() {
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [meta, setMeta] = useState<FrameMetadata | null>(null);
  const [status, setStatus] = useState<StatusDto | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [preset, setPreset] = useState<string | null>("full-body");
  const [tuning, setTuning] = useState<TuningValues>({
    dead_zone_pct: 0.08,
    damping: 0.12,
    max_speed_px: 40,
    confidence: 0.4,
  });

  const clientRef = useRef<StreamClient | null>(null);

  useEffect(() => {
    getSources().then(setSources).catch(() => setSources([]));
    const client = new StreamClient(
      (url, m) => {
        setImageUrl(url);
        setMeta(m);
        if (m) setStatus(m.status);
      },
      (s) => setStatus(s)
    );
    client.connect();
    clientRef.current = client;
    return () => client.close();
  }, []);

  const activeKey = status?.source_type ? sourceKey({ type: status.source_type, id: status.source_id ?? "" }) : null;
  const activeSource = sources.find((s) => sourceKey(s) === activeKey) ?? null;
  const running = !!status?.running;
  const tracking = !!status?.tracking;
  const selectedId = meta?.selected_track_id ?? null;
  const targetLost =
    tracking && selectedId !== null && !!meta && !meta.detections.some((d) => d.id === selectedId);

  async function handlePickSource(src: SourceInfo) {
    setStatus(await setSource(src.type, src.id));
  }

  async function handleToggle() {
    setStatus(await setTracking(tracking ? "stop" : "start"));
  }

  async function handlePreset(p: FramingPreset) {
    setPreset(p.key);
    await updateSettings({ target_fill_pct: p.fill, subject_portion: p.portion });
    if (running && !tracking) setStatus(await setTracking("start"));
  }

  async function handlePickPerson(id: number | null) {
    clientRef.current?.selectTarget(id);
    if (id !== null && !tracking) setStatus(await setTracking("start"));
  }

  function handleTuning(key: keyof TuningValues, value: number) {
    setTuning((t) => ({ ...t, [key]: value }));
    updateSettings({ [key]: value });
  }

  const closeSettings = useCallback(() => setSettingsOpen(false), []);

  let title = "No source selected";
  if (activeSource) {
    const name = activeSource.label;
    if (!running) title = `${name} · no signal`;
    else if (!tracking) title = `${name} · click a person or press Start to follow`;
    else if (selectedId === null) title = `${name} · looking for someone to follow`;
    else if (targetLost) title = `${name} · target ID ${selectedId} lost`;
    else title = `${name} · tracking ID ${selectedId}`;
  }

  const fps = status?.fps ?? 0;
  const fpsClass = !running ? "" : fps >= 20 ? "good" : fps >= 10 ? "warn" : "bad";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">Auto-Tracker</div>
        <div className="spacer" />
        <div className="telemetry">
          {status ? (
            <>
              <span className={fpsClass}>{fps.toFixed(1)} fps</span>
              <span className={status.dropped_frames > 0 ? "warn" : ""}>{status.dropped_frames} dropped</span>
              <span className={status.device.startsWith("cuda") ? "good" : ""}>{status.device}</span>
            </>
          ) : (
            <span className="warn">connecting…</span>
          )}
        </div>
        <button className="icon-btn" onClick={() => setSettingsOpen(true)} aria-label="Tracking settings">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0" />
            <circle cx="16" cy="6" r="2" />
            <circle cx="10" cy="12" r="2" />
            <circle cx="18" cy="18" r="2" />
          </svg>
        </button>
      </header>

      <div className="columns">
        <SourceList
          sources={sources}
          activeKey={activeKey}
          running={running}
          tracking={tracking}
          onPick={handlePickSource}
        />

        <main className="col-center">
          <div className={`title-strip${targetLost ? " lost" : ""}`}>{title}</div>
          <div className="preview-wrap">
            <div className="preview">
              {imageUrl ? (
                <PreviewCanvas imageUrl={imageUrl} meta={meta} onSelect={handlePickPerson} />
              ) : (
                <div className="preview-empty">
                  {status?.error ? (
                    <>
                      <strong>Camera unavailable</strong>
                      {status.error}. Close other apps using it, or pick another source.
                    </>
                  ) : activeSource ? (
                    <>
                      <strong>Starting camera…</strong>
                      The first start loads the detection model and can take a few seconds.
                    </>
                  ) : (
                    <>
                      <strong>No source</strong>
                      Pick a camera or video file on the left.
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
          <ControlDeck
            running={tracking}
            canStart={!!activeSource}
            onToggle={handleToggle}
            preset={preset}
            onPreset={handlePreset}
          />
        </main>

        <aside className="col-right">
          <OutputPanel imageUrl={imageUrl} meta={meta} live={tracking && !targetLost && selectedId !== null} />

          {status?.error && <div className="error-box">{status.error}</div>}

          <section>
            <h2 className="col-title">DIAGNOSTICS</h2>
            <dl className="diag">
              <dt>input</dt>
              <dd>{meta ? `${meta.w}×${meta.h}` : "—"}</dd>
              <dt>pipeline</dt>
              <dd>{running ? `${fps.toFixed(1)} fps` : "stopped"}</dd>
              <dt>dropped</dt>
              <dd>{status?.dropped_frames ?? 0}</dd>
              <dt>people</dt>
              <dd>{meta && running ? meta.detections.length : "—"}</dd>
              <dt>detector</dt>
              <dd>yolov8n · {status?.device ?? "—"}</dd>
            </dl>
          </section>
        </aside>
      </div>

      {settingsOpen && <SettingsModal values={tuning} onChange={handleTuning} onClose={closeSettings} />}
    </div>
  );
}
