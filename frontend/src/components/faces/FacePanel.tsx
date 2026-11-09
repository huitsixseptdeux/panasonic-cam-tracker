import { useEffect, useState } from "react";
import { personImageUrl } from "../../faceApi";
import type { FaceMode, Person } from "../../types";

interface Props {
  people: Person[];
  mode: FaceMode;
  personId: string | null;
  onChange: (mode: FaceMode, personId: string | null) => void;
  onManagePeople: () => void;
}

/** Main-screen face controls, modeled on Panasonic's Face Recognition group:
 *  ON/OFF, the selected face, and Auto Face Search. */
export function FacePanel({ people, mode, personId, onChange, onManagePeople }: Props) {
  const on = mode !== "off";
  const [auto, setAuto] = useState(mode === "auto");
  const [chosen, setChosen] = useState<string | null>(personId);
  const [picking, setPicking] = useState(false);

  useEffect(() => {
    if (mode !== "off") setAuto(mode === "auto");
    if (personId) setChosen(personId);
  }, [mode, personId]);

  const chosenPerson = people.find((p) => p.id === chosen) ?? null;
  // Panasonic: ON with no face selected follows any registered face.
  const modeFor = (a: boolean, c: string | null): FaceMode => (a || !c ? "auto" : "select");

  function toggle() {
    onChange(on ? "off" : modeFor(auto, chosen), chosen);
  }

  function setAutoSearch(v: boolean) {
    setAuto(v);
    if (on) onChange(modeFor(v, chosen), chosen);
  }

  function choose(id: string | null) {
    setChosen(id);
    setPicking(false);
    if (on) onChange(modeFor(auto, id), id);
  }

  if (people.length === 0) {
    return (
      <div className="deck-group">
        <div className="deck-label">FACE</div>
        <p className="hint">
          No faces registered.{" "}
          <button className="link-btn" onClick={onManagePeople}>
            Add people
          </button>{" "}
          to follow someone by face.
        </p>
      </div>
    );
  }

  return (
    <div className="deck-group">
      <div className="deck-label">FACE</div>
      <div className="face-row">
        <div className="face-col">
          <button
            className={`round round-lg${on ? " active" : ""}`}
            onClick={toggle}
            aria-pressed={on}
            aria-label={on ? "Turn face recognition off" : "Turn face recognition on"}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" />
              <circle cx="12" cy="10" r="3" />
              <path d="M7 17c1.2-2 3-3 5-3s3.8 1 5 3" />
            </svg>
          </button>
          <div className={`round-caption${on ? " on" : ""}`}>{on ? "On" : "Off"}</div>
        </div>

        <div className="face-col">
          <button className="face-pick" onClick={() => setPicking(true)} disabled={auto} title={auto ? "Turn off Auto face search to pick one person" : "Select face"}>
            {chosenPerson ? <img src={personImageUrl(chosenPerson.id)} alt="" /> : <span>?</span>}
          </button>
          <div className="round-caption">{auto ? "Anyone" : (chosenPerson?.name ?? "Select face")}</div>
        </div>

        <label className="check">
          <input type="checkbox" checked={auto} onChange={(e) => setAutoSearch(e.target.checked)} />
          Auto face search
        </label>
      </div>

      {picking && (
        <div className="modal-backdrop" onClick={() => setPicking(false)}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="select-face-title" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h2 id="select-face-title">Select face</h2>
              <button className="close-btn" onClick={() => setPicking(false)} aria-label="Close">
                ×
              </button>
            </div>
            <div className="select-grid">
              {people.map((p) => (
                <button key={p.id} className={`select-item${p.id === chosen ? " active" : ""}`} onClick={() => choose(p.id)}>
                  <img src={personImageUrl(p.id)} alt="" />
                  <span>{p.name}</span>
                </button>
              ))}
            </div>
            <button className="link-btn" style={{ alignSelf: "flex-start" }} onClick={onManagePeople}>
              Manage people…
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
