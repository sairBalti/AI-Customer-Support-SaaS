import type { ApiErrorBody } from "@/types/api";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message || "Request failed");
    this.name = "ApiError";
    this.status = status;
    this.code = body.code || "HTTP_ERROR";
    this.details = body.details;
  }
}

export function getErrorMessage(error: unknown, fallback = "Something went wrong") {
  if (error instanceof ApiError) {
    const details = formatValidationDetails(error.details);
    return details ? `${error.message} ${details}` : error.message;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

function formatValidationDetails(details: unknown): string | null {
  if (!details || typeof details !== "object") return null;
  const errors = (details as { errors?: unknown }).errors;
  if (!Array.isArray(errors) || errors.length === 0) return null;
  const parts = errors
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const row = item as { loc?: unknown[]; msg?: string };
      const field = Array.isArray(row.loc)
        ? row.loc.filter((part) => part !== "body").join(".")
        : "";
      const msg = row.msg || "Invalid value";
      return field ? `${field}: ${msg}` : msg;
    })
    .filter(Boolean);
  return parts.length ? `(${parts.join("; ")})` : null;
}
