import type { FramingSettings, FrameMetadata, SourceInfo, StatusDto } from "./types";

const API_BASE = "/api";

export async function getSources(): Promise<SourceInfo[]> {
  const res = await fetch(`${API_BASE}/sources`);
  const data = await res.json();
  return data.sources;
}

export async function setSource(type: string, id: string): Promise<StatusDto> {
  const res = await fetch(`${API_BASE}/source`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type, id }),
  });
  return res.json();
}

export async function setTracking(action: "start" | "stop"): Promise<StatusDto> {
  const res = await fetch(`${API_BASE}/tracking`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  return res.json();
}

export async function updateSettings(settings: FramingSettings): Promise<void> {
  await fetch(`${API_BASE}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
}

export type FrameHandler = (imageUrl: string, meta: FrameMetadata | null) => void;

export class StreamClient {
  private ws: WebSocket | null = null;
  private pendingBlobUrl: string | null = null;
  private onFrame: FrameHandler;
  private onStatusOnly: (status: StatusDto) => void;

  constructor(onFrame: FrameHandler, onStatusOnly: (status: StatusDto) => void) {
    this.onFrame = onFrame;
    this.onStatusOnly = onStatusOnly;
  }

  connect(): void {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    this.ws = new WebSocket(`${proto}://${window.location.host}/ws/stream`);
    this.ws.binaryType = "arraybuffer";

    this.ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        if (this.pendingBlobUrl) {
          URL.revokeObjectURL(this.pendingBlobUrl);
        }
        const blob = new Blob([event.data], { type: "image/jpeg" });
        this.pendingBlobUrl = URL.createObjectURL(blob);
        return;
      }
      const msg = JSON.parse(event.data);
      if (msg.status && msg.w === undefined) {
        this.onStatusOnly(msg.status as StatusDto);
        return;
      }
      if (this.pendingBlobUrl) {
        this.onFrame(this.pendingBlobUrl, msg as FrameMetadata);
      }
    };
  }

  selectTarget(trackId: number | null): void {
    this.ws?.send(JSON.stringify({ type: "select", track_id: trackId }));
  }

  close(): void {
    this.ws?.close();
    if (this.pendingBlobUrl) {
      URL.revokeObjectURL(this.pendingBlobUrl);
    }
  }
}
