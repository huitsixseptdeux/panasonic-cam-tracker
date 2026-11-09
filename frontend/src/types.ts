export interface SourceInfo {
  type: "webcam" | "file";
  id: string;
  label: string;
}

export interface DetectionDto {
  id: number;
  bbox: [number, number, number, number];
  conf: number;
}

export interface CropDto {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface StatusDto {
  running: boolean;
  tracking: boolean;
  source_open: boolean;
  source_type: string | null;
  source_id: string | null;
  fps: number;
  dropped_frames: number;
  device: string;
  selected_track_id: number | null;
  person_detected: boolean;
  error: string | null;
}

export interface FrameMetadata {
  w: number;
  h: number;
  detections: DetectionDto[];
  selected_track_id: number | null;
  crop: CropDto;
  status: StatusDto;
}

export interface StatusOnlyMessage {
  status: StatusDto;
}

export interface FramingSettings {
  dead_zone_pct?: number;
  damping?: number;
  max_speed_px?: number;
  target_fill_pct?: number;
  subject_portion?: number;
  confidence?: number;
}
