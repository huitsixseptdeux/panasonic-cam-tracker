import { useEffect } from "react";

export interface TuningValues {
  dead_zone_pct: number;
  damping: number;
  max_speed_px: number;
  confidence: number;
}

interface Props {
  values: TuningValues;
  onChange: (key: keyof TuningValues, value: number) => void;
  onClose: () => void;
}

const FIELDS: {
  key: keyof TuningValues;
  label: string;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  hint: string;
}[] = [
  {
    key: "dead_zone_pct",
    label: "Dead zone",
    min: 0,
    max: 0.3,
    step: 0.01,
    format: (v) => `${Math.round(v * 100)}%`,
    hint: "How far the subject can drift before the frame moves.",
  },
  {
    key: "damping",
    label: "Smoothing",
    min: 0.02,
    max: 0.6,
    step: 0.01,
    format: (v) => v.toFixed(2),
    hint: "Lower is calmer, higher follows faster.",
  },
  {
    key: "max_speed_px",
    label: "Max pan speed",
    min: 5,
    max: 200,
    step: 5,
    format: (v) => `${v} px/frame`,
    hint: "Caps how fast the frame can travel.",
  },
  {
    key: "confidence",
    label: "Detection confidence",
    min: 0.1,
    max: 0.9,
    step: 0.05,
    format: (v) => `${Math.round(v * 100)}%`,
    hint: "Raise it if furniture or posters get detected as people.",
  },
];

export function SettingsModal({ values, onChange, onClose }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <h2 id="settings-title">Tracking settings</h2>
          <button className="close-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        {FIELDS.map((f) => (
          <div className="field" key={f.key}>
            <div className="field-head">
              <label htmlFor={`set-${f.key}`}>{f.label}</label>
              <span className="field-value">{f.format(values[f.key])}</span>
            </div>
            <input
              id={`set-${f.key}`}
              className="rng"
              type="range"
              min={f.min}
              max={f.max}
              step={f.step}
              value={values[f.key]}
              onChange={(e) => onChange(f.key, parseFloat(e.target.value))}
            />
            <div className="field-hint">{f.hint}</div>
          </div>
        ))}

        <button className="done-btn" onClick={onClose}>
          Done
        </button>
      </div>
    </div>
  );
}
