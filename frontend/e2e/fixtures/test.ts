import fs from "node:fs";
import { test as base, expect, type Browser, type Page } from "@playwright/test";
import { apiLogin, storageStatePath } from "./api";
import { loadE2EEnv, type E2EEnv } from "./env";

type Role = keyof E2EEnv["users"];

type Fixtures = {
  env: E2EEnv;
  asSuperAdmin: Page;
  asCompanyAdmin: Page;
  asSupportManager: Page;
  asAgent: Page;
  asCustomer: Page;
  asFreePlanAdmin: Page;
};

export async function loginUi(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/app(\/|$)/);
}

async function authenticatedPage(browser: Browser, env: E2EEnv, role: Role) {
  const creds = env.users[role];
  const session = await apiLogin(env, creds.email, creds.password);
  const context = await browser.newContext({ baseURL: env.frontendUrl });
  const page = await context.newPage();

  // Set refresh once. Avoid addInitScript — it would overwrite the rotated refresh
  // token on later full-page navigations and force logout.
  await page.goto("/login");
  await page.evaluate((refreshToken: string) => {
    window.sessionStorage.setItem("acs_refresh_token", refreshToken);
  }, session.tokens.refresh_token);
  await page.goto("/app");
  if (page.url().includes("/login")) {
    await loginUi(page, creds.email, creds.password);
  }
  await expect(page.getByRole("button", { name: /logout/i })).toBeVisible({ timeout: 45_000 });

  try {
    fs.writeFileSync(
      storageStatePath(env, role),
      JSON.stringify(
        {
          email: creds.email,
          userId: session.user.user_id,
          companyId: session.user.company_id,
          roleName: session.user.role_name,
        },
        null,
        2,
      ),
      "utf8",
    );
  } catch {
    // ignore
  }

  return page;
}

export const test = base.extend<Fixtures>({
  env: async ({}, use) => {
    await use(loadE2EEnv());
  },
  asSuperAdmin: async ({ browser, env }, use) => {
    const page = await authenticatedPage(browser, env, "superAdmin");
    await use(page);
    await page.context().close();
  },
  asCompanyAdmin: async ({ browser, env }, use) => {
    const page = await authenticatedPage(browser, env, "companyAdmin");
    await use(page);
    await page.context().close();
  },
  asSupportManager: async ({ browser, env }, use) => {
    const page = await authenticatedPage(browser, env, "supportManager");
    await use(page);
    await page.context().close();
  },
  asAgent: async ({ browser, env }, use) => {
    const page = await authenticatedPage(browser, env, "agent");
    await use(page);
    await page.context().close();
  },
  asCustomer: async ({ browser, env }, use) => {
    const page = await authenticatedPage(browser, env, "customer");
    await use(page);
    await page.context().close();
  },
  asFreePlanAdmin: async ({ browser, env }, use) => {
    const page = await authenticatedPage(browser, env, "freePlanAdmin");
    await use(page);
    await page.context().close();
  },
});

export { expect };

export async function expectNavVisible(page: Page, label: string) {
  await expect(page.getByRole("navigation").getByRole("link", { name: label })).toBeVisible();
}

export async function expectNavHidden(page: Page, label: string) {
  await expect(page.getByRole("navigation").getByRole("link", { name: label })).toHaveCount(0);
}

export function uniqueSuffix() {
  return `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}
