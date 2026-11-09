import { useCallback, useEffect, useRef, useState } from "react";
import { getSources, setSource, setTracking, StreamClient, updateSettings } from "./api";
import { ControlDeck, type FramingPreset } from "./components/ControlDeck";
import { OutputPanel } from "./components/OutputPanel";
import { PreviewCanvas } from "./components/PreviewCanvas";
import { SettingsModal, type TuningValues } from "./components/SettingsModal";
import { SourceList, sourceKey } from "./components/SourceList";
import { FacePanel } from "./components/faces/FacePanel";
import { PeoplePage } from "./components/faces/PeoplePage";
import { listPeople, setRecognition } from "./faceApi";
import type { FaceMode, FrameMetadata, Person, SourceInfo, StatusDto } from "./types";

type View = "main" | "people";

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

  const [view, setView] = useState<View>("main");
  const [people, setPeople] = useState<Person[]>([]);
  const [faceError, setFaceError] = useState<string | null>(null);

  const clientRef = useRef<StreamClient | null>(null);

  const reloadPeople = useCallback(() => {
    listPeople()
      .then(setPeople)
      .catch(() => setPeople([]));
  }, []);

  useEffect(() => {
    getSources().then(setSources).catch(() => setSources([]));
    reloadPeople();
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
  }, [reloadPeople]);

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

  async function handleFace(mode: FaceMode, personId: string | null) {
    try {
      setFaceError(null);
      setStatus(await setRecognition(mode, personId));
      if (mode !== "off" && running && !tracking) setStatus(await setTracking("start"));
    } catch (e) {
      setFaceError((e as Error).message);
    }
  }

  function handleTuning(key: keyof TuningValues, value: number) {
    setTuning((t) => ({ ...t, [key]: value }));
    updateSettings({ [key]: value });
  }

  const closeSettings = useCallback(() => setSettingsOpen(false), []);

  const faceMode: FaceMode = status?.face_mode ?? "off";
  const facePersonId = status?.face_person_id ?? null;
  const wantedName =
    faceMode === "select" ? (people.find((p) => p.id === facePersonId)?.name ?? "the selected face") : "a registered face";
  const targetName = meta?.detections.find((d) => d.id === selectedId)?.person_name;
  const who = targetName ?? `ID ${selectedId}`;

  let title = "No source selected";
  if (activeSource) {
    const name = activeSource.label;
    if (!running) title = `${name} · no signal`;
    else if (!tracking) title = `${name} · click a person or press Start to follow`;
    else if (faceMode !== "off" && (selectedId === null || targetLost)) title = `${name} · looking for ${wantedName}`;
    else if (selectedId === null) title = `${name} · looking for someone to follow`;
    else if (targetLost) title = `${name} · ${who} lost`;
    else title = `${name} · tracking ${who}`;
  }

  const fps = status?.fps ?? 0;
  const fpsClass = !running ? "" : fps >= 20 ? "good" : fps >= 10 ? "warn" : "bad";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">Auto-Tracker</div>
        <nav className="tabs" aria-label="Screens">
          <button className={`tab${view === "main" ? " active" : ""}`} onClick={() => setView("main")}>
            MAIN
          </button>
          <button className={`tab${view === "people" ? " active" : ""}`} onClick={() => setView("people")}>
            PEOPLE
          </button>
        </nav>
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

      {view === "people" ? (
        <PeoplePage
          people={people}
          setPeople={setPeople}
          reload={reloadPeople}
          facesAvailable={status?.faces_available ?? true}
          canUseFrame={running}
          targetPersonId={faceMode === "select" ? facePersonId : null}
        />
      ) : (
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
            faceGroup={
              status?.faces_available ? (
                <FacePanel
                  people={people}
                  mode={faceMode}
                  personId={facePersonId}
                  onChange={handleFace}
                  onManagePeople={() => setView("people")}
                />
              ) : null
            }
          />
          {faceError && <div className="error-box deck-error">{faceError}</div>}
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
              <dt>faces</dt>
              <dd>{status?.faces_available ? faceMode : "unavailable"}</dd>
            </dl>
          </section>
        </aside>
      </div>
      )}

      {settingsOpen && <SettingsModal values={tuning} onChange={handleTuning} onClose={closeSettings} />}
    </div>
  );
}
