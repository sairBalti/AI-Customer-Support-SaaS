import { test, expect, uniqueSuffix } from "../fixtures/test";

test.describe("Audit", () => {
  test("list, filter, detail dialog for Super Admin", async ({ asSuperAdmin }) => {
    const page = asSuperAdmin;
    // Generate an auditable action first
    await page.goto("/app/tickets");
    const subject = `Audit Seed ${uniqueSuffix()}`;
    await page.getByRole("button", { name: /create ticket/i }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel(/^subject$/i).fill(subject);
    await dialog.getByLabel(/^description$/i).fill("Audit trail seed");
    await dialog.getByRole("button", { name: /^create$/i }).click();
    await expect(dialog).toBeHidden({ timeout: 20_000 });
    await expect(page.getByRole("link", { name: subject })).toBeVisible({ timeout: 20_000 });

    await page.goto("/app/audit");
    await expect(page.getByRole("heading", { name: /audit/i })).toBeVisible();
    await expect(page.getByRole("table")).toBeVisible();

    await page.getByLabel(/^action$/i).fill("tickets.create");
    const row = page.getByRole("row").filter({ hasText: "tickets.create" }).first();
    await expect(row).toBeVisible({ timeout: 30_000 });
    await row.click();
    await expect(page.getByRole("heading", { name: /audit entry detail/i })).toBeVisible();
    await expect(page.getByText(/UUID/i).first()).toBeVisible();
    await expect(page.getByText(/metadata/i).first()).toBeVisible();
    await expect(page.getByText(/user agent/i).first()).toBeVisible();
    await expect(page.getByText(/IP address/i).first()).toBeVisible();
  });

  test("Agent cannot open Audit", async ({ asAgent }) => {
    await asAgent.goto("/app/audit");
    await expect(asAgent).toHaveURL(/\/forbidden/);
  });
});
