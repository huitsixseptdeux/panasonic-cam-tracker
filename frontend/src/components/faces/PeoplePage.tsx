import { useState } from "react";
import { deletePerson, personImageUrl, renamePerson, reorderPeople } from "../../faceApi";
import type { Person } from "../../types";
import { AddFaceDialog } from "./AddFaceDialog";

interface Props {
  people: Person[];
  setPeople: (p: Person[]) => void;
  reload: () => void;
  facesAvailable: boolean;
  canUseFrame: boolean;
  targetPersonId: string | null;
}

export function PeoplePage({ people, setPeople, reload, facesAvailable, canUseFrame, targetPersonId }: Props) {
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!facesAvailable) {
    return (
      <div className="page">
        <div className="error-box">
          Face recognition is off: the face models are missing. Run <code>python scripts/fetch_assets.py</code> in{" "}
          <code>backend</code> and restart the backend.
        </div>
      </div>
    );
  }

  const filtered = query ? people.filter((p) => p.name.toLowerCase().includes(query.toLowerCase())) : people;

  async function saveName(id: string) {
    const name = editName.trim();
    setEditing(null);
    if (!name) return;
    try {
      await renamePerson(id, name);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function remove(id: string) {
    setConfirmDelete(null);
    try {
      await deletePerson(id);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function drop(targetId: string) {
    if (!dragId || dragId === targetId) return;
    const ids = people.map((p) => p.id).filter((id) => id !== dragId);
    ids.splice(ids.indexOf(targetId), 0, dragId);
    setDragId(null);
    const byId = Object.fromEntries(people.map((p) => [p.id, p]));
    setPeople(ids.map((id, i) => ({ ...byId[id], order: i })));
    try {
      setPeople(await reorderPeople(ids));
    } catch (e) {
      setError((e as Error).message);
      reload();
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">People</h1>
          <p className="field-hint">
            Registered faces. With Auto face search on, the person highest in this list wins when several are in
            shot. Drag to change the order.
          </p>
        </div>
        <div className="btn-row">
          <input
            className="text-input"
            placeholder="Search names"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search names"
          />
          <button className="done-btn" onClick={() => setAdding(true)}>
            + Add face
          </button>
        </div>
      </div>

      {error && (
        <div className="error-box" onClick={() => setError(null)}>
          {error}
        </div>
      )}

      {people.length === 0 ? (
        <div className="empty-people">
          <strong>No one registered yet.</strong>
          <span>Add a face from the live picture or from a photo. Then turn on Face recognition on the main screen.</span>
          <button className="done-btn" onClick={() => setAdding(true)}>
            + Add the first face
          </button>
        </div>
      ) : (
        <div className="people-grid">
          {filtered.map((p) => (
            <div
              key={p.id}
              className={`person-card${dragId === p.id ? " dragging" : ""}`}
              draggable={!query && editing !== p.id}
              onDragStart={() => setDragId(p.id)}
              onDragEnd={() => setDragId(null)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => drop(p.id)}
            >
              <span className="person-order">{p.order + 1}</span>
              <img className="person-photo" src={personImageUrl(p.id)} alt="" draggable={false} />
              {editing === p.id ? (
                <input
                  className="text-input"
                  autoFocus
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onBlur={() => saveName(p.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") saveName(p.id);
                    if (e.key === "Escape") setEditing(null);
                  }}
                  aria-label="Name"
                />
              ) : (
                <button
                  className="person-name"
                  onClick={() => {
                    setEditing(p.id);
                    setEditName(p.name);
                  }}
                  title="Rename"
                >
                  {p.name}
                </button>
              )}
              {p.id === targetPersonId && <span className="tag live person-tag">TARGET</span>}
              {p.stale && <span className="field-hint">Re-add: made with another face model</span>}
              {confirmDelete === p.id ? (
                <div className="btn-row">
                  <button className="danger-link" onClick={() => remove(p.id)}>
                    Delete
                  </button>
                  <button className="link-btn" onClick={() => setConfirmDelete(null)}>
                    Keep
                  </button>
                </div>
              ) : (
                <button className="link-btn" onClick={() => setConfirmDelete(p.id)}>
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {adding && (
        <AddFaceDialog
          canUseFrame={canUseFrame}
          onAdded={() => reload()}
          onClose={() => {
            setAdding(false);
            reload();
          }}
        />
      )}
    </div>
  );
}
