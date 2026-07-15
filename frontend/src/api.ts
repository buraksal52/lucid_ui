import type {
  AnalysisContext,
  AnalysisReport,
  ApiErrorPayload
} from "./types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, "");

interface SubmitAnalysisInput {
  file: File;
  context: AnalysisContext;
  description: string;
  runUiclip: boolean;
}

export class LucidApiError extends Error {
  code: string;
  details?: unknown;

  constructor(error: ApiErrorPayload) {
    super(error.message);
    this.name = "LucidApiError";
    this.code = error.code;
    this.details = error.details;
  }
}

async function readJson<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new LucidApiError({
      code: String(response.status),
      message: `Request returned ${response.status} without JSON.`
    });
  }

  return response.json() as Promise<T>;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return readJson<T>(response);
  }

  try {
    const body = await readJson<{ error?: ApiErrorPayload }>(response);
    throw new LucidApiError(
      body.error ?? {
        code: String(response.status),
        message: `Request failed with status ${response.status}.`
      }
    );
  } catch (error) {
    if (error instanceof LucidApiError) {
      throw error;
    }

    throw new LucidApiError({
      code: String(response.status),
      message: `Request failed with status ${response.status}.`
    });
  }
}

export async function submitSingleAnalysis({
  file,
  context,
  description,
  runUiclip
}: SubmitAnalysisInput): Promise<AnalysisReport> {
  const formData = new FormData();
  formData.append("image", file);
  formData.append("context", context);
  formData.append("runUiclip", String(runUiclip));

  const trimmedDescription = description.trim();
  if (trimmedDescription.length > 0) {
    formData.append("description", trimmedDescription);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/analyses/single`, {
    method: "POST",
    body: formData
  });

  return parseResponse<AnalysisReport>(response);
}

export async function fetchRawReport(analysisId: string): Promise<AnalysisReport> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/analyses/${analysisId}/raw`
  );

  return parseResponse<AnalysisReport>(response);
}
