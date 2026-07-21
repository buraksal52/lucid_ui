import type { ApiErrorPayload } from "./types";

export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;

export function validateFile(nextFile: File): ApiErrorPayload | null {
  if (!ACCEPTED_TYPES.includes(nextFile.type)) {
    return {
      code: "UNSUPPORTED_MEDIA_TYPE",
      message:
        "Select a PNG, JPG, or WebP screenshot before running analysis.",
      details: { contentType: nextFile.type, allowed: ACCEPTED_TYPES }
    };
  }

  if (nextFile.size > MAX_FILE_SIZE_BYTES) {
    return {
      code: "FILE_TOO_LARGE",
      message: "Select a screenshot under the 20 MB upload limit.",
      details: {
        sizeBytes: nextFile.size,
        maxBytes: MAX_FILE_SIZE_BYTES
      }
    };
  }

  return null;
}
