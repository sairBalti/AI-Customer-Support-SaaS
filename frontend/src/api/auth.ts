import { http, unwrapData } from "@/api/client";
import type { AuthSession, AuthUser } from "@/types/api";

export async function login(email: string, password: string) {
  const { data } = await http.post("/api/v1/auth/login", { email, password });
  return unwrapData<AuthSession>(data);
}

export async function logout(refreshToken?: string | null, revokeAll = true) {
  const { data } = await http.post("/api/v1/auth/logout", {
    refresh_token: refreshToken ?? undefined,
    revoke_all: revokeAll,
  });
  return unwrapData<null>(data);
}

export async function fetchMe() {
  const { data } = await http.get("/api/v1/auth/me");
  return unwrapData<AuthUser>(data);
}

export async function registerCompany(payload: {
  company_name: string;
  email: string;
  company_slug?: string;
  timezone?: string;
}) {
  const { data } = await http.post("/api/v1/companies", payload);
  return unwrapData(data);
}
