import { test, expect } from "../fixtures/test";

test.describe("Companies", () => {
  test("company list loads for Super Admin", async ({ asSuperAdmin }) => {
    await asSuperAdmin.goto("/app/companies");
    await expect(asSuperAdmin.getByRole("heading", { name: "Companies" })).toBeVisible();
    await expect(asSuperAdmin.getByRole("table")).toBeVisible();
    await expect(asSuperAdmin.getByRole("button", { name: /add company/i })).toBeVisible();
    await expect(asSuperAdmin.getByRole("columnheader", { name: /actions/i })).toBeVisible();
    await expect(asSuperAdmin.locator("#company-search")).toBeVisible();
    await expect(asSuperAdmin.getByLabel("Status")).toBeVisible();
    await expect(asSuperAdmin.getByLabel("Plan")).toBeVisible();
    await expect(asSuperAdmin.getByLabel("Sort by")).toBeVisible();
  });

  test("Super Admin can register a company from the list", async ({ asSuperAdmin }) => {
    const stamp = Date.now();
    const name = `E2E Admin Co ${stamp}`;
    const email = `e2e.admin.co.${stamp}@example.com`;
    await asSuperAdmin.goto("/app/companies");
    await asSuperAdmin.getByRole("button", { name: /add company/i }).click();
    const dialog = asSuperAdmin.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel(/company name/i).fill(name);
    await dialog.getByLabel(/ops email/i).fill(email);
    await dialog.getByRole("button", { name: /^create company$/i }).click();
    await expect(dialog).toBeHidden({ timeout: 20_000 });
    await asSuperAdmin.locator("#company-search").fill(name);
    await asSuperAdmin.getByRole("button", { name: /^search$/i }).click();
    await expect(asSuperAdmin.getByRole("link", { name })).toBeVisible({ timeout: 20_000 });
    await expect(asSuperAdmin.getByRole("link", { name: /^edit$/i }).first()).toBeVisible();
  });

  test("public company registration validates required fields", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: /register company/i })).toBeVisible();
    await page.getByRole("button", { name: /create company/i }).click();
    await expect(
      page.getByText(/required|min|invalid|email|too small|at least/i).first(),
    ).toBeVisible();
  });

  test("company registration creates a tenant and lands on sign in", async ({ page }) => {
    const stamp = Date.now();
    const name = `E2E Co ${stamp}`;
    const email = `e2e.reg.${stamp}@example.com`;
    const password = "E2e!RegisterPass12";
    await page.goto("/register");
    await page.getByLabel(/company name/i).fill(name);
    await page.getByLabel(/admin email/i).fill(email);
    await page.getByLabel(/^first name$/i).fill("E2E");
    await page.getByLabel(/^last name$/i).fill("Owner");
    await page.getByLabel(/^password$/i).fill(password);
    await page.getByLabel(/^confirm$/i).fill(password);
    await page.getByRole("button", { name: /create company/i }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
    await expect(page.getByText(/is ready|sign in with the admin/i)).toBeVisible();
    await expect(page.locator("#email")).toHaveValue(email);
    await page.locator("#password").click();
    await page.locator("#password").fill("");
    await page.locator("#password").pressSequentially(password, { delay: 10 });
    await expect(page.locator("#password")).toHaveValue(password);
    await page.getByRole("button", { name: /^sign in$/i }).click();
    await expect(page).toHaveURL(/\/app(\/|$)/, { timeout: 30_000 });
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });
});
