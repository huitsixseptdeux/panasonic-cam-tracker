import { useEffect, useRef } from "react";
import type { FrameMetadata } from "../types";

interface Props {
  imageUrl: string | null;
  meta: FrameMetadata | null;
  live: boolean;
}

const OUT_W = 640;
const OUT_H = 360;

export function OutputPanel({ imageUrl, meta, live }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(new Image());

  useEffect(() => {
    if (!imageUrl || !meta) return;
    const img = imgRef.current;
    img.onload = () => {
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (!canvas || !ctx) return;
      canvas.width = OUT_W;
      canvas.height = OUT_H;
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, OUT_W, OUT_H);
      const { x, y, w, h } = meta.crop;
      // Fit the crop into 16:9 without distorting it.
      const s = Math.min(OUT_W / w, OUT_H / h);
      const dw = w * s;
      const dh = h * s;
      ctx.drawImage(img, x, y, w, h, (OUT_W - dw) / 2, (OUT_H - dh) / 2, dw, dh);
    };
    img.src = imageUrl;
  }, [imageUrl, meta]);

  const zoom = meta ? (meta.w / meta.crop.w).toFixed(1) : null;

  return (
    <section>
      <h2 className="col-title">PROGRAM OUTPUT</h2>
      <div className={`output${live ? " live" : ""}`}>
        <canvas ref={canvasRef} />
        {zoom && <span className="output-badge">{zoom}× crop</span>}
      </div>
    </section>
  );
}
