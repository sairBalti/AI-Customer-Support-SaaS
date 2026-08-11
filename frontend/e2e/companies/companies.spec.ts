import { test, expect } from "../fixtures/test";

test.describe("Companies", () => {
  test("company list loads for Super Admin", async ({ asSuperAdmin }) => {
    await asSuperAdmin.goto("/app/companies");
    await expect(asSuperAdmin.getByRole("heading", { name: "Companies" })).toBeVisible();
    await expect(asSuperAdmin.getByRole("table")).toBeVisible();
  });

  test("public company registration validates required fields", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: /register company/i })).toBeVisible();
    await page.getByRole("button", { name: /create company/i }).click();
    await expect(page.getByText(/required|min|invalid|email|too small/i).first()).toBeVisible();
  });

  test("company registration creates a tenant", async ({ page }) => {
    const stamp = Date.now();
    const name = `E2E Co ${stamp}`;
    const email = `e2e.reg.${stamp}@example.com`;
    await page.goto("/register");
    await page.getByLabel(/company name/i).fill(name);
    await page.getByLabel(/ops email/i).fill(email);
    await page.getByRole("button", { name: /create company/i }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
  });
});
