import { useState, useRef, useEffect } from "react";
import {
  Upload,
  Sparkles,
  Flame,
  FileText,
  Download,
  Play,
  Pause,
  RotateCcw,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Film,
  Smartphone,
  Sliders,
  X,
} from "lucide-react";
import {
  uploadVideo,
  extractAudio,
  transcribeVideo,
  generateClips,
  exportShort,
  listExports,
} from "./api";
import type {
  VideoMetadata,
  TranscriptionData,
  TranscriptSegment,
  ClipCandidate,
  ExportMetadata,
} from "./api";
import "./App.css";

export default function App() {
  // Workflow State
  const [stage, setStage] = useState<"upload" | "processing" | "studio">("upload");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Video & Analysis Data
  const [videoId, setVideoId] = useState<string | null>(null);
  const [videoMeta, setVideoMeta] = useState<VideoMetadata | null>(null);
  const [transcription, setTranscription] = useState<TranscriptionData | null>(null);
  const [clips, setClips] = useState<ClipCandidate[]>([]);
  const [exportsList, setExportsList] = useState<ExportMetadata[]>([]);

  // Studio Active Tab
  const [activeTab, setActiveTab] = useState<"clips" | "transcript" | "exports">("clips");
  const [selectedClip, setSelectedClip] = useState<ClipCandidate | null>(null);
  const [expandedClipIndex, setExpandedClipIndex] = useState<number | null>(null);

  // Player & Simulator State
  const [playerMode, setPlayerMode] = useState<"player" | "simulator">("simulator");
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Export Modal State
  const [isExportModalOpen, setIsExportModalOpen] = useState<boolean>(false);
  const [exportClipTarget, setExportClipTarget] = useState<ClipCandidate | null>(null);
  const [aspectRatio, setAspectRatio] = useState<"9:16" | "original" | "1:1">("9:16");
  const [layout, setLayout] = useState<"blur_background" | "crop" | "fit">("blur_background");
  const [burnSubtitles, setBurnSubtitles] = useState<boolean>(true);
  const [subtitleColor, setSubtitleColor] = useState<"yellow" | "white" | "cyan" | "green">("yellow");
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportSuccess, setExportSuccess] = useState<ExportMetadata | null>(null);

  // File Upload Drag State
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Synchronize Player Time
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);

    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("play", handlePlay);
      video.removeEventListener("pause", handlePause);
    };
  }, [stage, playerMode]);

  // Load Exports whenever studio mounts or videoId changes
  useEffect(() => {
    if (videoId && stage === "studio") {
      listExports(videoId).then(setExportsList).catch(console.error);
    }
  }, [videoId, stage]);

  // Execute full automated pipeline
  const processVideoFile = async (file: File) => {
    try {
      setStage("processing");
      setCurrentStep(1);
      setStatusMessage("Uploading and validating video file...");

      // 1. Upload
      const uploadRes = await uploadVideo(file);
      const vId = uploadRes.video_id;
      setVideoId(vId);
      setVideoMeta(uploadRes.metadata);

      // 2. Extract Audio
      setCurrentStep(2);
      setStatusMessage("Extracting high-fidelity audio track with FFmpeg...");
      await extractAudio(vId);

      // 3. Transcribe with Whisper
      setCurrentStep(3);
      setStatusMessage("Running local Whisper speech recognition with VAD filtering...");
      const transcriptData = await transcribeVideo(vId);
      setTranscription(transcriptData);

      // 4. Clip Intelligence Engine
      setCurrentStep(4);
      setStatusMessage("Discovering engaging moments using 6-dimension scoring...");
      const clipsRes = await generateClips(vId);
      setClips(clipsRes.clips);
      if (clipsRes.clips.length > 0) {
        setSelectedClip(clipsRes.clips[0]);
      }

      // Transition to Studio
      setStage("studio");
    } catch (err: any) {
      console.error(err);
      alert(`Processing error: ${err.message || err}`);
      setStage("upload");
    }
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processVideoFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processVideoFile(e.target.files[0]);
    }
  };

  const loadSampleVideo = async () => {
    try {
      setStage("processing");
      setCurrentStep(1);
      setStatusMessage("Loading sample demonstration video...");
      const res = await fetch("/sample_demo.mp4");
      const blob = await res.blob();
      const file = new File([blob], "sample_clip.mp4", { type: "video/mp4" });
      await processVideoFile(file);
    } catch (err: any) {
      console.error(err);
      alert(`Could not load sample video: ${err.message || err}`);
      setStage("upload");
    }
  };

  // Preview a clip in player and seek to its start
  const playClip = (clip: ClipCandidate) => {
    setSelectedClip(clip);
    if (videoRef.current) {
      videoRef.current.currentTime = clip.start;
      videoRef.current.play();
    }
  };

  // Trigger export
  const handleExport = async () => {
    if (!videoId) return;
    try {
      setIsExporting(true);
      setExportSuccess(null);

      const params = exportClipTarget
        ? {
            clip_index: exportClipTarget.clip_index,
            aspect_ratio: aspectRatio,
            layout: layout,
            burn_subtitles: burnSubtitles,
            subtitle_color: subtitleColor,
          }
        : {
            start: selectedClip?.start || 0,
            end: selectedClip?.end || 10,
            aspect_ratio: aspectRatio,
            layout: layout,
            burn_subtitles: burnSubtitles,
            subtitle_color: subtitleColor,
          };

      const result = await exportShort(videoId, params);
      setExportSuccess(result.export);
      // Refresh exports list
      const updated = await listExports(videoId);
      setExportsList(updated);
    } catch (err: any) {
      console.error(err);
      alert(`Export failed: ${err.message || err}`);
    } finally {
      setIsExporting(false);
    }
  };

  // Current caption for live simulator
  const activeCaption = transcription?.segments.find(
    (s: TranscriptSegment) => currentTime >= s.start && currentTime <= s.end
  )?.text;

  // Video URL (served through static storage mount)
  const videoSrc = videoMeta && videoId ? `/storage/uploads/${videoMeta.filename}` : "";

  return (
    <div className="app-container">
      {/* Ambient Radial Lighting */}
      <div className="ambient-glow" />

      {/* Navigation Bar */}
      <header className="navbar liquid-glass">
        <div className="nav-brand">
          <div className="logo-icon">
            <Sparkles size={20} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className="brand-name">ClipForge AI</span>
              <span className="brand-badge">Local AI</span>
            </div>
          </div>
        </div>

        {/* Workflow Stepper */}
        <div className="workflow-stepper">
          <div className={`step-item ${stage === "upload" ? "active" : "completed"}`}>
            <span className="step-dot" />
            <span>1. Upload</span>
          </div>
          <span style={{ color: "rgba(255,255,255,0.2)" }}>›</span>
          <div className={`step-item ${stage === "processing" && currentStep <= 3 ? "active" : stage === "studio" ? "completed" : ""}`}>
            <span className="step-dot" />
            <span>2. Transcribe</span>
          </div>
          <span style={{ color: "rgba(255,255,255,0.2)" }}>›</span>
          <div className={`step-item ${stage === "processing" && currentStep === 4 ? "active" : stage === "studio" ? "completed" : ""}`}>
            <span className="step-dot" />
            <span>3. Discover</span>
          </div>
          <span style={{ color: "rgba(255,255,255,0.2)" }}>›</span>
          <div className={`step-item ${stage === "studio" ? "active" : ""}`}>
            <span className="step-dot" />
            <span>4. Studio</span>
          </div>
        </div>

        <div className="nav-actions">
          <div className="offline-pill">
            <span className="status-indicator" />
            <span>100% Offline & Free</span>
          </div>
          {stage === "studio" && (
            <button
              className="btn-secondary"
              onClick={() => {
                if (confirm("Upload a new video? This will reset the current workspace.")) {
                  setStage("upload");
                  setVideoId(null);
                  setClips([]);
                  setTranscription(null);
                }
              }}
            >
              New Video
            </button>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {/* ====================================================================
            STAGE 1: Upload Dropzone
           ==================================================================== */}
        {stage === "upload" && (
          <div className="upload-hero">
            <div className="hero-tag">
              <Sparkles size={14} /> Turn Long Videos Into Viral Shorts
            </div>
            <h1 className="title-display">
              Autonomous Video Discovery <br />
              Powered by Local AI
            </h1>
            <p className="hero-subtitle">
              Drop any long-form video or podcast. ClipForge automatically transcribes speech,
              analyzes viral hook potential across 6 dimensions, and generates 9:16 Shorts with
              stylized captions.
            </p>

            <div
              className={`dropzone-container ${isDragOver ? "drag-over" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
                style={{ display: "none" }}
                onChange={handleFileSelect}
              />
              <div className="dropzone-icon">
                <Upload size={32} />
              </div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>
                Choose a video or drag & drop here
              </h3>
              <p className="body-regular">MP4, MOV, WEBM, or MKV up to 5 GB</p>

              <div className="upload-specs">
                <div className="spec-badge">
                  <CheckCircle2 size={14} color="#10b981" /> No API Keys Needed
                </div>
                <div className="spec-badge">
                  <CheckCircle2 size={14} color="#10b981" /> 100% Private on Your PC
                </div>
              </div>
            </div>

            <div style={{ marginTop: "1.75rem", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.75rem" }}>
              <span className="caption-meta">Or try immediately without uploading:</span>
              <button
                className="btn-secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  loadSampleVideo();
                }}
              >
                <Sparkles size={14} color="#818cf8" />
                <span>Try With Sample Video</span>
              </button>
            </div>
          </div>
        )}

        {/* ====================================================================
            STAGE 2: Processing Progress Indicator
           ==================================================================== */}
        {stage === "processing" && (
          <div style={{ maxWidth: "560px", margin: "6rem auto", textAlign: "center" }}>
            <div
              className="dropzone-icon"
              style={{ width: "80px", height: "80px", marginBottom: "2rem" }}
            >
              <Sparkles size={40} className="animate-spin" />
            </div>
            <h2 className="title-section" style={{ fontSize: "1.5rem", marginBottom: "0.75rem" }}>
              Forging Clips with Local Intelligence
            </h2>
            <p className="body-regular" style={{ marginBottom: "2rem" }}>
              {statusMessage}
            </p>

            {/* Step Progress Pills */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.75rem",
                textAlign: "left",
                background: "var(--bg-surface)",
                padding: "1.5rem",
                borderRadius: "var(--radius-lg)",
                border: "1px solid rgba(255,255,255,0.08)",
              }}
            >
              {[
                { step: 1, label: "Video Upload & Validation" },
                { step: 2, label: "Audio Extraction (16kHz Mono WAV)" },
                { step: 3, label: "Faster-Whisper Transcription & VAD" },
                { step: 4, label: "6-Dimension Viral Scoring & Deduplication" },
              ].map((item) => (
                <div
                  key={item.step}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0.5rem 0.75rem",
                    borderRadius: "var(--radius-sm)",
                    background:
                      currentStep === item.step
                        ? "rgba(99,102,241,0.1)"
                        : "transparent",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.875rem",
                      fontWeight: currentStep === item.step ? 600 : 400,
                      color:
                        currentStep === item.step
                          ? "var(--text-primary)"
                          : currentStep > item.step
                          ? "var(--accent-success)"
                          : "var(--text-tertiary)",
                    }}
                  >
                    {item.label}
                  </span>
                  {currentStep > item.step ? (
                    <CheckCircle2 size={16} color="#10b981" />
                  ) : currentStep === item.step ? (
                    <span
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--accent-primary)",
                        fontWeight: 600,
                      }}
                    >
                      Working...
                    </span>
                  ) : (
                    <span style={{ fontSize: "0.75rem", color: "var(--text-quaternary)" }}>
                      Pending
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ====================================================================
            STAGE 3: Studio Workspace (Dual-Pane)
           ==================================================================== */}
        {stage === "studio" && (
          <div className="studio-grid">
            {/* Left Column: Clips, Transcript, Exports */}
            <div className="studio-left">
              {/* Segmented Control */}
              <div className="segmented-bar">
                <button
                  className={`segment-btn ${activeTab === "clips" ? "active" : ""}`}
                  onClick={() => setActiveTab("clips")}
                >
                  <Flame size={15} /> Viral Clips ({clips.length})
                </button>
                <button
                  className={`segment-btn ${activeTab === "transcript" ? "active" : ""}`}
                  onClick={() => setActiveTab("transcript")}
                >
                  <FileText size={15} /> Full Transcript
                </button>
                <button
                  className={`segment-btn ${activeTab === "exports" ? "active" : ""}`}
                  onClick={() => setActiveTab("exports")}
                >
                  <Download size={15} /> Exported Shorts ({exportsList.length})
                </button>
              </div>

              {/* TAB 1: Viral Clips */}
              {activeTab === "clips" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  {clips.map((clip: ClipCandidate) => {
                    const isSelected = selectedClip?.clip_index === clip.clip_index;
                    const isExpanded = expandedClipIndex === clip.clip_index;

                    return (
                      <div
                        key={clip.clip_index}
                        className={`clip-card ${isSelected ? "selected" : ""}`}
                        onClick={() => setSelectedClip(clip)}
                      >
                        {/* Header */}
                        <div className="clip-card-header">
                          <div className="clip-badge-group">
                            <span className="clip-rank">#{clip.clip_index}</span>
                            <span className="time-pill">
                              {clip.start_formatted} – {clip.end_formatted} ({Math.round(clip.duration)}s)
                            </span>
                          </div>

                          {/* Quality Score */}
                          <div
                            className={`score-badge ${
                              clip.clip_quality_score >= 80 ? "score-high" : "score-mid"
                            }`}
                          >
                            <Flame size={14} />
                            <span>{clip.clip_quality_score}</span>
                            <span style={{ fontSize: "0.6875rem", opacity: 0.8 }}>/ 100</span>
                          </div>
                        </div>

                        {/* Text */}
                        <p className="clip-text">"{clip.text}"</p>

                        {/* Reason Tags */}
                        <div className="reasons-tags">
                          {clip.reasons.slice(0, 3).map((r: string, i: number) => (
                            <span key={i} className="reason-pill">
                              ✓ {r}
                            </span>
                          ))}
                        </div>

                        {/* Expandable 6-Dimension Score Breakdown */}
                        <div>
                          <button
                            className="breakdown-toggle"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedClipIndex(isExpanded ? null : clip.clip_index);
                            }}
                          >
                            <span>Quality Score Breakdown</span>
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>

                          {isExpanded && (
                            <div className="breakdown-grid" style={{ marginTop: "0.75rem" }}>
                              <div className="metric-box">
                                <span className="metric-name">Hook</span>
                                <span className="metric-value">{clip.scores.hook}/20</span>
                              </div>
                              <div className="metric-box">
                                <span className="metric-name">Info Value</span>
                                <span className="metric-value">{clip.scores.information}/20</span>
                              </div>
                              <div className="metric-box">
                                <span className="metric-name">Emotion</span>
                                <span className="metric-value">{clip.scores.emotion}/15</span>
                              </div>
                              <div className="metric-box">
                                <span className="metric-name">Context</span>
                                <span className="metric-value">{clip.scores.context}/20</span>
                              </div>
                              <div className="metric-box">
                                <span className="metric-name">Completeness</span>
                                <span className="metric-value">{clip.scores.completeness}/15</span>
                              </div>
                              <div className="metric-box">
                                <span className="metric-name">Pacing</span>
                                <span className="metric-value">{clip.scores.pacing}/10</span>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Actions */}
                        <div className="clip-card-actions">
                          <button
                            className="btn-secondary"
                            onClick={(e) => {
                              e.stopPropagation();
                              playClip(clip);
                            }}
                          >
                            <Play size={14} /> Preview
                          </button>
                          <button
                            className="btn-primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExportClipTarget(clip);
                              setIsExportModalOpen(true);
                            }}
                          >
                            <Download size={14} /> Export Short
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* TAB 2: Full Transcript */}
              {activeTab === "transcript" && (
                <div
                  style={{
                    background: "var(--bg-surface)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "var(--radius-xl)",
                    padding: "1.5rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "1rem",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      paddingBottom: "0.75rem",
                      borderBottom: "1px solid rgba(255,255,255,0.08)",
                    }}
                  >
                    <span className="caption-meta">
                      Language: {transcription?.language.toUpperCase()} • Segments:{" "}
                      {transcription?.segment_count}
                    </span>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                    {transcription?.segments.map((seg: TranscriptSegment, i: number) => (
                      <div
                        key={i}
                        style={{
                          display: "flex",
                          gap: "1rem",
                          padding: "0.5rem",
                          borderRadius: "var(--radius-sm)",
                          cursor: "pointer",
                          transition: "background var(--transition-fast)",
                        }}
                        onMouseEnter={(e) =>
                          (e.currentTarget.style.background = "rgba(255,255,255,0.04)")
                        }
                        onMouseLeave={(e) =>
                          (e.currentTarget.style.background = "transparent")
                        }
                        onClick={() => {
                          if (videoRef.current) {
                            videoRef.current.currentTime = seg.start;
                            videoRef.current.play();
                          }
                        }}
                      >
                        <span
                          className="time-pill"
                          style={{
                            alignSelf: "flex-start",
                            fontSize: "0.75rem",
                            flexShrink: 0,
                          }}
                        >
                          {Math.floor(seg.start)}s
                        </span>
                        <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)" }}>
                          {seg.text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 3: Exported Shorts */}
              {activeTab === "exports" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  {exportsList.length === 0 ? (
                    <div
                      style={{
                        padding: "3rem",
                        textAlign: "center",
                        background: "var(--bg-surface)",
                        borderRadius: "var(--radius-xl)",
                        border: "1px solid rgba(255,255,255,0.08)",
                      }}
                    >
                      <Film size={36} color="var(--text-tertiary)" style={{ margin: "0 auto 1rem" }} />
                      <h4 style={{ fontWeight: 600, marginBottom: "0.5rem" }}>
                        No Shorts exported yet
                      </h4>
                      <p className="body-regular">
                        Select any viral clip and click "Export Short" to render vertical 9:16 video.
                      </p>
                    </div>
                  ) : (
                    exportsList.map((exp: ExportMetadata) => (
                      <div
                        key={exp.export_id}
                        className="clip-card"
                        style={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}
                      >
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.4rem" }}>
                            <span style={{ fontWeight: 600 }}>{exp.filename}</span>
                            <span className="time-pill">{exp.duration_formatted}</span>
                            <span className="reason-pill">{exp.aspect_ratio}</span>
                          </div>
                          <span className="caption-meta">
                            {exp.file_size_mb} MB • {exp.width}x{exp.height} • Subtitles: {exp.burn_subtitles ? "Burned-in" : "None"}
                          </span>
                        </div>

                        <a
                          href={`/api/export/${exp.export_id}/download`}
                          download={exp.filename}
                          className="btn-primary"
                          style={{ textDecoration: "none" }}
                        >
                          <Download size={15} /> Download MP4
                        </a>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Right Column: Studio Player & 9:16 Phone Simulator */}
            <div className="studio-right">
              <div className="player-card">
                <div className="player-view-switch">
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button
                      className={`btn-ghost ${playerMode === "simulator" ? "active" : ""}`}
                      style={{
                        fontWeight: playerMode === "simulator" ? 600 : 400,
                        color: playerMode === "simulator" ? "var(--text-primary)" : "var(--text-tertiary)",
                        borderBottom: playerMode === "simulator" ? "2px solid var(--accent-primary)" : "none",
                        borderRadius: 0,
                      }}
                      onClick={() => setPlayerMode("simulator")}
                    >
                      <Smartphone size={15} /> 9:16 Shorts Simulator
                    </button>
                    <button
                      className={`btn-ghost ${playerMode === "player" ? "active" : ""}`}
                      style={{
                        fontWeight: playerMode === "player" ? 600 : 400,
                        color: playerMode === "player" ? "var(--text-primary)" : "var(--text-tertiary)",
                        borderBottom: playerMode === "player" ? "2px solid var(--accent-primary)" : "none",
                        borderRadius: 0,
                      }}
                      onClick={() => setPlayerMode("player")}
                    >
                      <Film size={15} /> Source Video
                    </button>
                  </div>

                  <span className="caption-meta">
                    {Math.floor(currentTime)}s / {videoMeta ? Math.floor(videoMeta.duration_seconds) : 0}s
                  </span>
                </div>

                {/* Simulated 9:16 Phone Frame */}
                {playerMode === "simulator" ? (
                  <div className="phone-simulator-container">
                    <div className="phone-bezel">
                      <div className="phone-screen">
                        {/* Background Blurred Video */}
                        <div
                          className="phone-bg-blur"
                          style={{
                            backgroundImage: `radial-gradient(circle, rgba(99,102,241,0.2) 0%, #000 80%)`,
                          }}
                        />

                        {/* Actual HTML5 Video */}
                        <video
                          ref={videoRef}
                          src={videoSrc}
                          className="phone-fg-video"
                          playsInline
                        />

                        {/* Live Stylized Subtitle Overlay */}
                        {activeCaption && (
                          <div className="phone-caption-overlay">
                            <span className={`caption-bubble caption-${subtitleColor}`}>
                              {activeCaption}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Standard Landscape Video Player */
                  <div style={{ borderRadius: "var(--radius-md)", overflow: "hidden", background: "#000" }}>
                    <video
                      ref={videoRef}
                      src={videoSrc}
                      controls
                      style={{ width: "100%", maxHeight: "300px", display: "block" }}
                    />
                  </div>
                )}

                {/* Player Transport Controls */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "0.5rem" }}>
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button
                      className="btn-secondary"
                      onClick={() => {
                        if (videoRef.current) {
                          if (isPlaying) videoRef.current.pause();
                          else videoRef.current.play();
                        }
                      }}
                    >
                      {isPlaying ? <Pause size={15} /> : <Play size={15} />}
                      <span>{isPlaying ? "Pause" : "Play"}</span>
                    </button>
                    {selectedClip && (
                      <button
                        className="btn-secondary"
                        onClick={() => {
                          if (videoRef.current) {
                            videoRef.current.currentTime = selectedClip.start;
                            videoRef.current.play();
                          }
                        }}
                      >
                        <RotateCcw size={15} /> Replay Clip
                      </button>
                    )}
                  </div>

                  {selectedClip && (
                    <button
                      className="btn-primary"
                      onClick={() => {
                        setExportClipTarget(selectedClip);
                        setIsExportModalOpen(true);
                      }}
                    >
                      <Download size={15} /> Export Short
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ====================================================================
          Export Customization Modal Sheet
         ==================================================================== */}
      {isExportModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsExportModalOpen(false)}>
          <div className="modal-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Sliders size={18} color="var(--accent-primary)" />
                <h3 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Export Vertical Short</h3>
              </div>
              <button
                className="btn-ghost"
                style={{ padding: "0.3rem" }}
                onClick={() => setIsExportModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {/* Aspect Ratio */}
              <div className="form-group">
                <label className="form-label">Aspect Ratio</label>
                <div className="choice-row">
                  <button
                    className={`choice-btn ${aspectRatio === "9:16" ? "active" : ""}`}
                    onClick={() => setAspectRatio("9:16")}
                  >
                    9:16 Shorts
                  </button>
                  <button
                    className={`choice-btn ${aspectRatio === "1:1" ? "active" : ""}`}
                    onClick={() => setAspectRatio("1:1")}
                  >
                    1:1 Square
                  </button>
                  <button
                    className={`choice-btn ${aspectRatio === "original" ? "active" : ""}`}
                    onClick={() => setAspectRatio("original")}
                  >
                    Original
                  </button>
                </div>
              </div>

              {/* 9:16 Layout */}
              {aspectRatio === "9:16" && (
                <div className="form-group">
                  <label className="form-label">9:16 Framing Layout</label>
                  <div className="choice-row">
                    <button
                      className={`choice-btn ${layout === "blur_background" ? "active" : ""}`}
                      onClick={() => setLayout("blur_background")}
                    >
                      Blurred Background
                    </button>
                    <button
                      className={`choice-btn ${layout === "crop" ? "active" : ""}`}
                      onClick={() => setLayout("crop")}
                    >
                      Center Crop
                    </button>
                    <button
                      className={`choice-btn ${layout === "fit" ? "active" : ""}`}
                      onClick={() => setLayout("fit")}
                    >
                      Letterbox (Fit)
                    </button>
                  </div>
                </div>
              )}

              {/* Subtitles Toggle & Color */}
              <div className="form-group">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <label className="form-label">Burn-In Stylized Captions</label>
                  <input
                    type="checkbox"
                    checked={burnSubtitles}
                    onChange={(e) => setBurnSubtitles(e.target.checked)}
                    style={{ width: "16px", height: "16px", accentColor: "var(--accent-primary)" }}
                  />
                </div>

                {burnSubtitles && (
                  <div style={{ marginTop: "0.5rem" }}>
                    <label className="caption-meta" style={{ display: "block", marginBottom: "0.4rem" }}>
                      Caption Highlight Color
                    </label>
                    <div className="color-picker-row">
                      {[
                        { id: "yellow", color: "#ffff00", name: "Yellow" },
                        { id: "white", color: "#ffffff", name: "White" },
                        { id: "cyan", color: "#00ffff", name: "Cyan" },
                        { id: "green", color: "#00ff55", name: "Green" },
                      ].map((c) => (
                        <div
                          key={c.id}
                          className={`color-circle ${subtitleColor === c.id ? "active" : ""}`}
                          style={{ background: c.color }}
                          title={c.name}
                          onClick={() => setSubtitleColor(c.id as any)}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {exportSuccess && (
                <div
                  style={{
                    padding: "1rem",
                    borderRadius: "var(--radius-md)",
                    background: "var(--accent-success-bg)",
                    border: "1px solid rgba(16,185,129,0.3)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: "var(--accent-success)", fontSize: "0.875rem" }}>
                      Ready for Download!
                    </div>
                    <div className="caption-meta">{exportSuccess.file_size_mb} MB • MP4</div>
                  </div>
                  <a
                    href={`/api/export/${exportSuccess.export_id}/download`}
                    download={exportSuccess.filename}
                    className="btn-primary"
                    style={{ textDecoration: "none", fontSize: "0.8125rem", padding: "0.4rem 0.8rem" }}
                  >
                    <Download size={14} /> Download
                  </a>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setIsExportModalOpen(false)}>
                Cancel
              </button>
              <button
                className="btn-primary"
                disabled={isExporting}
                onClick={handleExport}
              >
                {isExporting ? (
                  <>
                    <Sparkles size={15} className="animate-spin" /> Rendering Short...
                  </>
                ) : (
                  <>
                    <Film size={15} /> Render & Export Short
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
