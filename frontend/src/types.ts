export type AnalysisContext = "general" | "expert";

export type AnalysisStatus =
  | "queued"
  | "processing"
  | "completed"
  | "partial_success"
  | "failed";

export type StageStatus =
  | "completed"
  | "disabled"
  | "unavailable"
  | "fallback"
  | "failed";

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: unknown;
}

export interface ImageMetadata {
  width?: number;
  height?: number;
  format?: string;
  aspectRatio?: number;
  orientation?: string;
  fileSizeBytes?: number;
}

export interface MetricSection {
  id: string;
  title: string;
  category: string;
  rawDisplay: string;
  normalizedScore: number | null;
  explanation: string;
  evidencePaths: string[];
  source: string | null;
  isProxy: boolean;
}

export interface CompositeSummary {
  rawDisplay: string;
  value: number;
  scoreName: string;
  context: AnalysisContext | string;
  explanation: string;
}

export interface UIClipSummary {
  status: StageStatus;
  modelId: string | null;
  userDescription: string | null;
  rawScoreDisplay: string | null;
  scoreType: string | null;
  normalizedScoreDisplay: string | null;
  comparableToLucidui: boolean;
  comparabilityNote: string;
}

export interface PresentationReport {
  title: string;
  context: AnalysisContext | string;
  summary: string;
  metricSections: MetricSection[];
  composite: CompositeSummary;
  uiclipSummary: UIClipSummary;
  recommendations: string[];
  limitations: string[];
  closingNote: string;
}

export interface LlmObservation {
  id: string;
  text: string;
  metricEvidence: string[];
  category: string;
}

export interface LlmInterpretation {
  status: StageStatus;
  provider: string | null;
  summary: string | null;
  observations: LlmObservation[];
  recommendations: string[];
  limitations: string[];
}

export interface UiclipReport {
  enabled: boolean;
  status: StageStatus;
  modelVersion: string | null;
  description: string | null;
  descriptionSource: "user" | "generic" | "generated" | string;
  qualityScore: number | null;
  normalizedQualityScore: number | null;
  observations: string[];
  inferenceTimeMs: number | null;
}

export interface Timings {
  totalMs?: number;
  luciduiMs?: number;
  llmMs?: number;
  uiclipMs?: number;
  comparisonMs?: number;
}

export interface AnalysisReport {
  schemaVersion: string;
  analysisId: string;
  mode: "single" | string;
  context: AnalysisContext | string;
  status: AnalysisStatus;
  imageMetadata: ImageMetadata;
  lucidui: Record<string, unknown>;
  llmInterpretation: LlmInterpretation;
  uiclip: UiclipReport;
  comparison: Record<string, unknown>;
  timings: Timings;
  note: string;
  presentation: PresentationReport;
}
