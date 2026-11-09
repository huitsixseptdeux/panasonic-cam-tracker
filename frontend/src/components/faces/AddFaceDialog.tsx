import { useEffect, useRef, useState } from "react";
import { findCandidates, registerFace } from "../../faceApi";
import type { CandidatesResponse, Person } from "../../types";

interface Props {
  canUseFrame: boolean;
  onAdded: (p: Person) => void;
  onClose: () => void;
}

export function AddFaceDialog({ canUseFrame, onAdded, onClose }: Props) {
  const [data, setData] = useState<CandidatesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [added, setAdded] = useState<Record<string, string>>({});
  const fileRef = useRef<HTMLInputElement>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function detect(image?: string) {
    setLoading(true);
    setError(null);
    setPicked(null);
    setAdded({});
    try {
      const res = await findCandidates(image);
      setData(res);
      if (res.faces.length === 0) setError("No face found. Try a closer, front-facing photo.");
      else if (res.faces.length === 1) pick(res.faces[0].token);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function pick(token: string) {
    setPicked(token);
    setName("");
    setTimeout(() => nameRef.current?.focus(), 0);
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => detect(String(reader.result));
    reader.readAsDataURL(file);
  }

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!picked || !name.trim()) return;
    try {
      const person = await registerFace(picked, name.trim());
      setAdded((a) => ({ ...a, [picked]: person.name }));
      onAdded(person);
      setPicked(null);
      setName("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const pickedFace = data?.faces.find((f) => f.token === picked);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-wide" role="dialog" aria-modal="true" aria-labelledby="add-face-title" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2 id="add-face-title">Add a face</h2>
          <button className="close-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="btn-row">
          <button className="ghost-btn" onClick={() => detect()} disabled={!canUseFrame || loading}>
            Use the live picture
          </button>
          <button className="ghost-btn" onClick={() => fileRef.current?.click()} disabled={loading}>
            Upload a photo…
          </button>
          <input ref={fileRef} type="file" accept="image/jpeg,image/png" hidden onChange={onFile} />
        </div>
        {!canUseFrame && <p className="field-hint">Pick a source on the main screen to use the live picture.</p>}

        {loading && <p className="field-hint">Looking for faces…</p>}
        {error && <div className="error-box">{error}</div>}

        {data && data.faces.length > 0 && (
          <>
            <p className="field-hint">
              {data.faces.length === 1 ? "One face found." : `${data.faces.length} faces found. Click the one to add.`}
            </p>
            <div className="cand-stage">
              <img src={`data:image/jpeg;base64,${data.image}`} alt="" />
              {data.faces.map((f) => {
                const [x1, y1, x2, y2] = f.bbox;
                const done = added[f.token];
                return (
                  <button
                    key={f.token}
                    className={`cand-box${f.token === picked ? " picked" : ""}${done ? " done" : ""}`}
                    style={{
                      left: `${(x1 / data.width) * 100}%`,
                      top: `${(y1 / data.height) * 100}%`,
                      width: `${((x2 - x1) / data.width) * 100}%`,
                      height: `${((y2 - y1) / data.height) * 100}%`,
                    }}
                    onClick={() => !done && pick(f.token)}
                    aria-label={done ? `Added as ${done}` : "Pick this face"}
                  >
                    {done && <span className="cand-label">{done}</span>}
                  </button>
                );
              })}
            </div>
          </>
        )}

        {pickedFace && (
          <form className="add-row" onSubmit={add}>
            <img className="face-thumb-lg" src={`data:image/jpeg;base64,${pickedFace.thumb}`} alt="" />
            <div className="field" style={{ flex: 1 }}>
              <label htmlFor="face-name">Name</label>
              <input
                id="face-name"
                ref={nameRef}
                className="text-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Marie"
                maxLength={40}
              />
              {pickedFace.matches && (
                <span className="field-hint">Looks like {pickedFace.matches}, who is already registered.</span>
              )}
            </div>
            <button className="done-btn" type="submit" disabled={!name.trim()}>
              Add
            </button>
          </form>
        )}

        <button className="ghost-btn" style={{ alignSelf: "flex-end" }} onClick={onClose}>
          Done
        </button>
      </div>
    </div>
  );
}
