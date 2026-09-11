/**
 * ClipForge AI — API Client
 */

export interface VideoMetadata {
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  file_size_mb: number;
  duration_seconds: number;
  duration_formatted: string;
  width: number;
  height: number;
  codec: string;
  fps: number | null;
}

export interface VideoUploadResult {
  video_id: string;
  message: string;
  metadata: VideoMetadata;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

export interface TranscriptionData {
  video_id: string;
  text: string;
  language: string;
  duration: number;
  segment_count: number;
  segments: TranscriptSegment[];
}

export interface ClipScores {
  hook: number;
  information: number;
  emotion: number;
  context: number;
  completeness: number;
  pacing: number;
}

export interface ClipCandidate {
  clip_index: number;
  start: number;
  end: number;
  duration: number;
  start_formatted: string;
  end_formatted: string;
  text: string;
  clip_quality_score: number;
  scores: ClipScores;
  reasons: string[];
  segment_count: number;
}

export interface ClipGenerationResult {
  message: string;
  video_id: string;
  clip_count: number;
  clips: ClipCandidate[];
}

export interface ExportMetadata {
  export_id: string;
  video_id: string;
  clip_index: number | null;
  start: number;
  end: number;
  duration: number;
  duration_formatted: string;
  aspect_ratio: string;
  layout: string;
  burn_subtitles: boolean;
  filename: string;
  file_size_bytes: number;
  file_size_mb: number;
  width: number;
  height: number;
  created_at: string;
}

export interface ExportResult {
  message: string;
  export: ExportMetadata;
  download_url: string;
}

const API_BASE = "";

export async function uploadVideo(file: File): Promise<VideoUploadResult> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/videos/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with status ${res.status}`);
  }

  return res.json();
}

export async function extractAudio(videoId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/videos/${videoId}/extract-audio`, {
    method: "POST",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Audio extraction failed: ${res.status}`);
  }

  return res.json();
}

export async function transcribeVideo(videoId: string): Promise<TranscriptionData> {
  const res = await fetch(`${API_BASE}/api/transcription/${videoId}/transcribe`, {
    method: "POST",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Transcription failed: ${res.status}`);
  }

  const data = await res.json();
  return data.result;
}

export async function generateClips(
  videoId: string,
  maxClips: number = 10,
  regenerate: boolean = false
): Promise<ClipGenerationResult> {
  const res = await fetch(`${API_BASE}/api/clips/${videoId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ max_clips: maxClips, regenerate }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Clip generation failed: ${res.status}`);
  }

  return res.json();
}

export async function getExistingClips(videoId: string): Promise<ClipGenerationResult | null> {
  const res = await fetch(`${API_BASE}/api/clips/${videoId}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load clips: ${res.status}`);
  return res.json();
}

export interface ExportParams {
  clip_index?: number;
  start?: number;
  end?: number;
  aspect_ratio?: "9:16" | "original" | "1:1";
  layout?: "blur_background" | "crop" | "fit";
  burn_subtitles?: boolean;
  subtitle_color?: "yellow" | "white" | "cyan" | "green";
}

export async function exportShort(
  videoId: string,
  params: ExportParams
): Promise<ExportResult> {
  const res = await fetch(`${API_BASE}/api/export/${videoId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Export failed: ${res.status}`);
  }

  return res.json();
}

export async function listExports(videoId: string): Promise<ExportMetadata[]> {
  const res = await fetch(`${API_BASE}/api/export/list/${videoId}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.exports || [];
}
