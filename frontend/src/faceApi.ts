import type { CandidatesResponse, FaceMode, Person, StatusDto } from "./types";

const API = "/api";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const personImageUrl = (id: string) => `${API}/faces/${id}/image`;

export async function listPeople(): Promise<Person[]> {
  return (await call<{ people: Person[] }>("/faces")).people;
}

/** Detect faces in an uploaded image (data URL), or in the current frame when omitted. */
export function findCandidates(image?: string): Promise<CandidatesResponse> {
  return call("/faces/candidates", { method: "POST", body: JSON.stringify({ image: image ?? null }) });
}

export function registerFace(token: string, name: string): Promise<Person> {
  return call("/faces", { method: "POST", body: JSON.stringify({ token, name }) });
}

export function renamePerson(id: string, name: string): Promise<Person> {
  return call(`/faces/${id}`, { method: "PATCH", body: JSON.stringify({ name }) });
}

export function deletePerson(id: string): Promise<{ ok: boolean }> {
  return call(`/faces/${id}`, { method: "DELETE" });
}

export async function reorderPeople(ids: string[]): Promise<Person[]> {
  return (await call<{ people: Person[] }>("/faces/order", { method: "PUT", body: JSON.stringify({ ids }) })).people;
}

export function setRecognition(mode: FaceMode, personId: string | null): Promise<StatusDto> {
  return call("/recognition", { method: "POST", body: JSON.stringify({ mode, person_id: personId }) });
}
