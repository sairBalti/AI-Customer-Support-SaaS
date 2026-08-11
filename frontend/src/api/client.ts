import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { ApiError } from "@/lib/api-error";
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setCurrentUser,
  setSession,
} from "@/lib/auth-store";
import type { AuthSession } from "@/types/api";

const baseURL = import.meta.env.VITE_API_BASE_URL || "";

export const http = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    // Allow the runtime to set multipart boundary.
    delete config.headers["Content-Type"];
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  try {
    const { data } = await axios.post<{ success: boolean; data: AuthSession }>(
      `${baseURL}/api/v1/auth/refresh`,
      { refresh_token: refresh },
    );
    if (!data.success) return null;
    setSession(data.data.tokens, data.data.user);
    return data.data.tokens.access_token;
  } catch {
    clearSession();
    return null;
  }
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ success?: boolean; error?: { code: string; message: string; details?: unknown } }>) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const status = error.response?.status;
    const code = error.response?.data?.error?.code;

    const shouldRefresh =
      status === 401 &&
      !original._retry &&
      code !== "INVALID_CREDENTIALS" &&
      !original.url?.includes("/auth/login") &&
      !original.url?.includes("/auth/refresh");

    if (shouldRefresh) {
      original._retry = true;
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const token = await refreshPromise;
      if (token) {
        setAccessToken(token);
        original.headers.Authorization = `Bearer ${token}`;
        return http(original);
      }
      clearSession();
      setCurrentUser(null);
    }

    const body = error.response?.data?.error ?? {
      code: "NETWORK_ERROR",
      message: error.message || "Network error",
    };
    throw new ApiError(status ?? 0, body);
  },
);

export function unwrapData<T>(payload: { success: boolean; data: T; message?: string | null }) {
  return payload.data;
}
