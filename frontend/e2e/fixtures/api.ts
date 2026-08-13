import fs from "node:fs";
import path from "node:path";
import { loadE2EEnv, type E2EEnv } from "./env";

type Envelope<T> = { success: boolean; data: T; message?: string | null; error?: { message: string } };

async function api<T>(
  env: E2EEnv,
  method: string,
  apiPath: string,
  opts?: { token?: string; body?: unknown; formData?: FormData },
): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts?.token) headers.Authorization = `Bearer ${opts.token}`;
  let body: BodyInit | undefined;
  if (opts?.formData) {
    body = opts.formData;
  } else if (opts?.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(`${env.apiBaseUrl}${apiPath}`, { method, headers, body });
  const text = await res.text();
  let json: Envelope<T>;
  try {
    json = JSON.parse(text) as Envelope<T>;
  } catch {
    throw new Error(
      `${method} ${apiPath} failed (${res.status}): non-JSON response: ${text.slice(0, 400)}`,
    );
  }
  if (!res.ok || json.success === false) {
    throw new Error(
      `${method} ${apiPath} failed (${res.status}): ${json.error?.message || JSON.stringify(json)}`,
    );
  }
  return json.data;
}

export type AuthSession = {
  tokens: { access_token: string; refresh_token: string };
  user: {
    user_id: number;
    company_id: number;
    email: string;
    role_name: string;
    permissions: string[];
    is_super_admin: boolean;
    first_name: string;
    last_name: string;
    display_name: string | null;
  };
};

export async function apiLogin(env: E2EEnv, email: string, password: string) {
  return api<AuthSession>(env, "POST", "/api/v1/auth/login", {
    body: { email, password },
  });
}

/**
 * Idempotent E2E bootstrap:
 * - Keeps shared role users (`e2e.company.admin@…`, manager, agent, customer) on the
 *   Super Admin tenant (or `E2E_COMPANY_ID`) so RAG/chat share one knowledge space.
 * - Ensures a separate FREE-plan company (`e2e-tenant`) plus a dedicated Company Admin
 *   used only for plan upload-limit tests.
 * - Creates missing E2E users only; never deletes tenants/users/documents; never
 *   mutates non-E2E emails.
 */
export async function ensureSeedUsers(env: E2EEnv = loadE2EEnv()) {
  const health = await fetch(`${env.apiBaseUrl}/health`);
  if (!health.ok) {
    throw new Error(
      `Backend health check failed at ${env.apiBaseUrl}/health. Start Docker backend before E2E.`,
    );
  }

  const sa = await apiLogin(env, env.users.superAdmin.email, env.users.superAdmin.password);
  const token = sa.tokens.access_token;
  const sharedCompanyId = env.companyId ?? sa.user.company_id;
  const freeCompanyId = await ensureE2ECompany(env, token);

  const usersPage = await api<{
    items: Array<{ email: string; user_id: number; company_id: number }>;
  }>(env, "GET", `/api/v1/users?page=1&page_size=100`, { token });
  const byEmail = new Map(usersPage.items.map((u) => [u.email.toLowerCase(), u]));

  const sharedUsers = [
    {
      email: env.users.companyAdmin.email,
      password: env.users.companyAdmin.password,
      role_name: "COMPANY_ADMIN",
      first_name: "E2E",
      last_name: "CompanyAdmin",
      company_id: sharedCompanyId,
    },
    {
      email: env.users.supportManager.email,
      password: env.users.supportManager.password,
      role_name: "SUPPORT_MANAGER",
      first_name: "E2E",
      last_name: "Manager",
      company_id: sharedCompanyId,
    },
    {
      email: env.users.agent.email,
      password: env.users.agent.password,
      role_name: "SUPPORT_AGENT",
      first_name: "E2E",
      last_name: "Agent",
      company_id: sharedCompanyId,
    },
    {
      email: env.users.customer.email,
      password: env.users.customer.password,
      role_name: "CUSTOMER",
      first_name: "E2E",
      last_name: "Customer",
      company_id: sharedCompanyId,
    },
    {
      email: env.users.freePlanAdmin.email,
      password: env.users.freePlanAdmin.password,
      role_name: "COMPANY_ADMIN",
      first_name: "E2E",
      last_name: "FreeAdmin",
      company_id: freeCompanyId,
    },
  ] as const;

  for (const user of sharedUsers) {
    const existing = byEmail.get(user.email.toLowerCase());
    if (existing) continue;
    await api(env, "POST", "/api/v1/users", {
      token,
      body: {
        email: user.email,
        password: user.password,
        first_name: user.first_name,
        last_name: user.last_name,
        role_name: user.role_name,
        company_id: user.company_id,
      },
    });
  }

  return {
    companyId: sharedCompanyId,
    freeCompanyId,
    superAdminUserId: sa.user.user_id,
  };
}

async function ensureE2ECompany(env: E2EEnv, token: string): Promise<number> {
  const slug = env.companySlug;
  const listed = await api<{
    items: Array<{ company_id: number; company_slug: string; subscription_plan: string }>;
  }>(env, "GET", `/api/v1/companies?page=1&page_size=100&search=${encodeURIComponent(slug)}`, {
    token,
  });
  const found = listed.items.find((c) => c.company_slug === slug);
  if (found) {
    if (found.subscription_plan !== "FREE") {
      await api(env, "PATCH", `/api/v1/companies/${found.company_id}/subscription`, {
        token,
        body: { subscription_plan: "FREE" },
      });
    }
    return found.company_id;
  }

  const created = await api<{ company_id: number }>(env, "POST", "/api/v1/companies", {
    token,
    body: {
      company_name: "E2E Free Tenant",
      company_slug: slug,
      email: `ops.${slug.replace(/[^a-z0-9]/gi, "")}@example.com`,
      subscription_plan: "FREE",
      activate_trial: false,
    },
  });
  return created.company_id;
}

export function storageStatePath(env: E2EEnv, role: keyof E2EEnv["users"]) {
  return path.join(env.authDir, `${role}.json`);
}

export function ensureAuthDir(env: E2EEnv) {
  fs.mkdirSync(env.authDir, { recursive: true });
}
