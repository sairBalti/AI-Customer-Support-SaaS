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
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}
