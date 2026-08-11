import fs from "node:fs";
import type { FullConfig } from "@playwright/test";
import { apiLogin, ensureAuthDir, ensureSeedUsers, storageStatePath } from "./fixtures/api";
import { loadE2EEnv } from "./fixtures/env";

/**
 * Seed role users via API and write lightweight role metadata files.
 * Authenticated fixtures perform a fresh API login per test (refresh rotates).
 */
export default async function globalSetup(_config: FullConfig) {
  const env = loadE2EEnv();
  ensureAuthDir(env);
  const seeded = await ensureSeedUsers(env);

  const roles = [
    ["superAdmin", env.users.superAdmin],
    ["companyAdmin", env.users.companyAdmin],
    ["supportManager", env.users.supportManager],
    ["agent", env.users.agent],
    ["customer", env.users.customer],
    ["freePlanAdmin", env.users.freePlanAdmin],
  ] as const;

  for (const [key, creds] of roles) {
    const session = await apiLogin(env, creds.email, creds.password);
    fs.writeFileSync(
      storageStatePath(env, key),
      JSON.stringify(
        {
          email: creds.email,
          userId: session.user.user_id,
          companyId: session.user.company_id ?? seeded.companyId,
          roleName: session.user.role_name,
        },
        null,
        2,
      ),
      "utf8",
    );
  }
}
