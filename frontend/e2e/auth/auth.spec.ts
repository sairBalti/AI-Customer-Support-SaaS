import { test, expect, loginUi, expectNavVisible } from "../fixtures/test";

test.describe("Auth", () => {
  test("login with valid credentials reaches dashboard", async ({ page, env }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await loginUi(page, env.users.superAdmin.email, env.users.superAdmin.password);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText(/Super Admin|SUPER_ADMIN/i).first()).toBeVisible();
    await page.goto("/app/documents");
    await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
  });

  test("invalid login shows error and stays on login", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("nobody@example.com");
    await page.getByLabel("Password").fill("DefinitelyWrong1!");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText(/invalid|failed|credentials|unauthorized/i).first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page).toHaveURL(/\/login/);
  });

  test("unauthenticated users are redirected from protected routes", async ({ page }) => {
    const routes = [
      "/app/companies",
      "/app/users",
      "/app/documents",
      "/app/knowledge",
      "/app/chat",
      "/app/tickets",
      "/app/audit",
    ];
    for (const route of routes) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
    }
  });

  test("logout returns to login and blocks protected pages", async ({ page, env }) => {
    await loginUi(page, env.users.superAdmin.email, env.users.superAdmin.password);
    await expectNavVisible(page, "Documents");
    await page.getByRole("button", { name: /logout/i }).click();
    await expect(page).toHaveURL(/\/login/);
    await page.goto("/app/documents");
    await expect(page).toHaveURL(/\/login/);
  });
});
