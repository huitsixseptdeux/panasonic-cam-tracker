import type { SourceInfo } from "../types";

interface Props {
  sources: SourceInfo[];
  activeKey: string | null;
  running: boolean;
  tracking: boolean;
  onPick: (source: SourceInfo) => void;
}

export const sourceKey = (s: { type: string; id: string }) => `${s.type}:${s.id}`;

function SourceIcon({ type }: { type: SourceInfo["type"] }) {
  if (type === "file") {
    return (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <path d="M10 9.5v5l4-2.5z" />
      </svg>
    );
  }
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <rect x="3" y="7" width="13" height="10" rx="2" />
      <path d="M16 11l5-3v8l-5-3z" />
    </svg>
  );
}

export function SourceList({ sources, activeKey, running, tracking, onPick }: Props) {
  return (
    <aside className="col-left">
      <h2 className="col-title">SOURCES</h2>
      {sources.length === 0 && (
        <p className="empty-note">
          No camera found. Plug in a webcam, or drop an .mp4 into <code>backend/samples/</code> and reload.
        </p>
      )}
      {sources.map((s) => {
        const key = sourceKey(s);
        const active = key === activeKey;
        const tag = active ? (tracking ? "TRACKING" : running ? "LIVE" : "STOP") : null;
        return (
          <button key={key} className={`tile${active ? " selected" : ""}`} onClick={() => onPick(s)}>
            <div className="tile-thumb">
              <SourceIcon type={s.type} />
              {tag && <span className={`tag${tracking ? " live" : ""}`}>{tag}</span>}
            </div>
            <div className="tile-row">
              <span>{s.label}</span>
              <span className="tile-meta">{s.type}</span>
            </div>
          </button>
        );
      })}
    </aside>
  );
}
