import { useEffect, useRef } from "react";
import type { FrameMetadata } from "../types";

interface Props {
  imageUrl: string | null;
  meta: FrameMetadata | null;
  onSelect: (trackId: number | null) => void;
}

const CYAN = "#4cc9f0";
const OTHER = "rgba(236,236,238,0.55)";
const YELLOW = "#f2c94c";

export function PreviewCanvas({ imageUrl, meta, onSelect }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(new Image());

  useEffect(() => {
    if (!imageUrl) return;
    const img = imgRef.current;
    img.onload = () => draw();
    img.src = imageUrl;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageUrl, meta]);

  function draw() {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img.complete) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    ctx.drawImage(img, 0, 0);
    if (!meta) return;

    const scale = Math.max(1, canvas.width / 960);
    ctx.font = `${Math.round(11 * scale)}px 'JetBrains Mono', monospace`;

    for (const det of meta.detections) {
      const [x1, y1, x2, y2] = det.bbox;
      const selected = det.id === meta.selected_track_id;
      ctx.strokeStyle = selected ? CYAN : OTHER;
      ctx.lineWidth = (selected ? 2 : 1) * scale;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      if (det.face_bbox) {
        const [fx1, fy1, fx2, fy2] = det.face_bbox;
        ctx.strokeStyle = YELLOW;
        ctx.lineWidth = 1.5 * scale;
        ctx.strokeRect(fx1, fy1, fx2 - fx1, fy2 - fy1);
      }

      const label = det.person_name ? `${det.person_name} · ${det.id}` : `ID ${det.id}`;
      const pad = 4 * scale;
      const lh = 15 * scale;
      const tw = ctx.measureText(label).width + pad * 2;
      const ly = Math.max(0, y1 - lh);
      ctx.fillStyle = selected ? CYAN : OTHER;
      ctx.fillRect(x1, ly, tw, lh);
      ctx.fillStyle = "#0b0b0c";
      ctx.fillText(label, x1 + pad, ly + lh - 4 * scale);
    }

    const c = meta.crop;
    ctx.strokeStyle = "rgba(255,255,255,0.7)";
    ctx.setLineDash([6 * scale, 4 * scale]);
    ctx.lineWidth = 1 * scale;
    ctx.strokeRect(c.x, c.y, c.w, c.h);
    ctx.setLineDash([]);
  }

  function handleClick(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas || !meta) return;
    const rect = canvas.getBoundingClientRect();
    // object-fit: contain letterboxes the bitmap inside the element; undo that.
    const s = Math.min(rect.width / canvas.width, rect.height / canvas.height);
    const offX = (rect.width - canvas.width * s) / 2;
    const offY = (rect.height - canvas.height * s) / 2;
    const x = (e.clientX - rect.left - offX) / s;
    const y = (e.clientY - rect.top - offY) / s;

    const hit = meta.detections.find((d) => {
      const [x1, y1, x2, y2] = d.bbox;
      return x >= x1 && x <= x2 && y >= y1 && y <= y2;
    });
    onSelect(hit ? hit.id : null);
  }

  return <canvas ref={canvasRef} onClick={handleClick} />;
}
