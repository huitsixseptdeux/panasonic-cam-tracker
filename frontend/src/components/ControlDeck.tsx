export interface FramingPreset {
  key: string;
  short: string;
  label: string;
  fill: number;
  portion: number;
}

// Mirrors Panasonic's Upper Body / Full Body / Full angle presets: `portion` is
// how much of the body (from the head down) is framed, `fill` how much of the
// output height that portion occupies.
export const PRESETS: FramingPreset[] = [
  { key: "upper", short: "UB", label: "Upper body", fill: 0.7, portion: 0.45 },
  { key: "full-body", short: "FB", label: "Full body", fill: 0.8, portion: 1.0 },
  { key: "wide", short: "W", label: "Wide", fill: 0.4, portion: 1.0 },
];

interface Props {
  running: boolean;
  canStart: boolean;
  onToggle: () => void;
  preset: string | null;
  onPreset: (p: FramingPreset) => void;
}

export function ControlDeck({ running, canStart, onToggle, preset, onPreset }: Props) {
  return (
    <div className="deck">
      <div className="deck-group">
        <div className="deck-label">TRACKING</div>
        <button
          className={`round round-lg${running ? " active" : ""}`}
          onClick={onToggle}
          disabled={!running && !canStart}
          aria-label={running ? "Stop tracking" : "Start tracking"}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <circle cx="12" cy="12" r="6" />
            <path d="M12 2v5M12 17v5M2 12h5M17 12h5" />
          </svg>
        </button>
        <div className={`round-caption${running ? " on" : ""}`}>{running ? "Stop" : "Start"}</div>
      </div>

      <div className="deck-group">
        <div className="deck-label">FRAMING</div>
        <div className="preset-row">
          {PRESETS.map((p) => (
            <div className="preset" key={p.key}>
              <button
                className={`round round-md${preset === p.key ? " active" : ""}`}
                onClick={() => onPreset(p)}
                aria-label={p.label}
                aria-pressed={preset === p.key}
              >
                {p.short}
              </button>
              <span>{p.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="deck-group">
        <div className="deck-label">TARGET</div>
        <p className="hint">Click a person in the image to track them. Click empty space to release.</p>
      </div>
    </div>
  );
}
