import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(rootDir, "../..");

function readDotEnvFile(filePath: string) {
  if (!fs.existsSync(filePath)) return;
  const text = fs.readFileSync(filePath, "utf8");
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

export type E2EEnv = {
  frontendUrl: string;
  apiBaseUrl: string;
  password: string;
  users: {
    superAdmin: { email: string; password: string };
    companyAdmin: { email: string; password: string };
    supportManager: { email: string; password: string };
    agent: { email: string; password: string };
    customer: { email: string; password: string };
    /** Dedicated Company Admin on FREE `e2e-tenant` for oversized-upload assertions. */
    freePlanAdmin: { email: string; password: string };
  };
  companyId: number | null;
  /** Stable slug for the dedicated FREE-plan E2E tenant (upload size-limit tests). */
  companySlug: string;
  authDir: string;
};

export function loadE2EEnv(): E2EEnv {
  readDotEnvFile(path.join(frontendRoot, ".env.e2e"));
  const password = process.env.E2E_PASSWORD || "E2e!LocalPass12";
  return {
    frontendUrl: process.env.E2E_FRONTEND_URL || "http://127.0.0.1:5175",
    apiBaseUrl: process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000",
    password,
    users: {
      superAdmin: {
        email: process.env.E2E_SUPERADMIN_EMAIL || "superadmin@platform.com",
        password: process.env.E2E_SUPERADMIN_PASSWORD || "Str0ng!Password",
      },
      companyAdmin: {
        email: process.env.E2E_COMPANY_ADMIN_EMAIL || "e2e.company.admin@platform.com",
        password: process.env.E2E_COMPANY_ADMIN_PASSWORD || password,
      },
      supportManager: {
        email: process.env.E2E_SUPPORT_MANAGER_EMAIL || "e2e.support.manager@platform.com",
        password: process.env.E2E_SUPPORT_MANAGER_PASSWORD || password,
      },
      agent: {
        email: process.env.E2E_AGENT_EMAIL || "e2e.agent@platform.com",
        password: process.env.E2E_AGENT_PASSWORD || password,
      },
      customer: {
        email: process.env.E2E_CUSTOMER_EMAIL || "e2e.customer@platform.com",
        password: process.env.E2E_CUSTOMER_PASSWORD || password,
      },
      freePlanAdmin: {
        email: process.env.E2E_FREE_ADMIN_EMAIL || "e2e.free.admin@platform.com",
        password: process.env.E2E_FREE_ADMIN_PASSWORD || password,
      },
    },
    companyId: process.env.E2E_COMPANY_ID ? Number(process.env.E2E_COMPANY_ID) : null,
    companySlug: process.env.E2E_COMPANY_SLUG || "e2e-tenant",
    authDir: path.join(frontendRoot, "e2e/.auth"),
  };
}
