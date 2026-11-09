export interface SourceInfo {
  type: "webcam" | "file";
  id: string;
  label: string;
}

export type BBox = [number, number, number, number];

export interface DetectionDto {
  id: number;
  bbox: BBox;
  conf: number;
  face_bbox?: BBox | null;
  person_id?: string | null;
  person_name?: string | null;
}

export type FaceMode = "off" | "select" | "auto";

export interface Person {
  id: string;
  name: string;
  order: number;
  stale: boolean;
}

export interface FaceCandidate {
  token: string;
  bbox: BBox;
  thumb: string;
  matches: string | null;
}

export interface CandidatesResponse {
  width: number;
  height: number;
  image: string;
  faces: FaceCandidate[];
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
  face_mode?: FaceMode;
  face_person_id?: string | null;
  faces_available?: boolean;
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
