import { test, expect, uniqueSuffix } from "../fixtures/test";
import fs from "node:fs";
import { storageStatePath } from "../fixtures/api";

test.describe("Tickets", () => {
  test("create ticket and filter by status", async ({ asSuperAdmin }) => {
    const page = asSuperAdmin;
    const subject = `E2E Ticket ${uniqueSuffix()}`;
    await page.goto("/app/tickets");
    await page.getByRole("button", { name: /create ticket/i }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel(/^subject$/i).fill(subject);
    await dialog.getByLabel(/^description$/i).fill("Created by Playwright E2E");
    await dialog.getByRole("button", { name: /^create$/i }).click();
    await expect(page.getByText(/ticket created/i).first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("link", { name: subject })).toBeVisible();

    await page.getByLabel(/status/i).selectOption("OPEN");
    await expect(page.getByRole("link", { name: subject })).toBeVisible();
  });

  test("assign → resolve → close workflow", async ({ asSuperAdmin, env }) => {
    const page = asSuperAdmin;
    const subject = `E2E Flow ${uniqueSuffix()}`;
    const auth = JSON.parse(fs.readFileSync(storageStatePath(env, "superAdmin"), "utf8")) as {
      userId: number;
    };

    await page.goto("/app/tickets");
    await page.getByRole("button", { name: /create ticket/i }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel(/^subject$/i).fill(subject);
    await dialog.getByLabel(/^description$/i).fill("Workflow E2E");
    await dialog.getByRole("button", { name: /^create$/i }).click();
    await page.getByRole("link", { name: subject }).click();
    await expect(page).toHaveURL(/\/app\/tickets\/\d+/);
    await expect(page.getByText("OPEN").first()).toBeVisible();

    await page.getByPlaceholder(/user id/i).fill(String(auth.userId));
    await page.getByRole("button", { name: /^assign$/i }).click();
    await expect(page.getByText(/ticket assigned|IN_PROGRESS/i).first()).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByText("IN_PROGRESS").first()).toBeVisible();

    await page.getByRole("button", { name: /^resolve$/i }).click();
    await expect(page.getByText("RESOLVED").first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("button", { name: /^resolve$/i })).toHaveCount(0);

    page.once("dialog", (d) => d.accept());
    await page.getByRole("button", { name: /^close$/i }).click();
    await expect(page.getByText("CLOSED").first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("button", { name: /^assign$/i })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^close$/i })).toHaveCount(0);
  });

  test("Customer can create tickets; cannot access assign controls", async ({ asCustomer }) => {
    const page = asCustomer;
    const subject = `E2E Cust ${uniqueSuffix()}`;
    await page.goto("/app/tickets");
    await page.getByRole("button", { name: /create ticket/i }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel(/^subject$/i).fill(subject);
    await dialog.getByLabel(/^description$/i).fill("Customer created ticket");
    await dialog.getByRole("button", { name: /^create$/i }).click();
    await expect(page.getByRole("link", { name: subject })).toBeVisible({ timeout: 20_000 });
    await page.getByRole("link", { name: subject }).click();
    await expect(page.getByRole("button", { name: /^assign$/i })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^resolve$/i })).toHaveCount(0);
  });
});
