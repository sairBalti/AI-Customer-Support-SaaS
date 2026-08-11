import { test, expect, uniqueSuffix } from "../fixtures/test";
import fs from "node:fs";
import { storageStatePath } from "../fixtures/api";

/**
 * Primary smoke journey:
 * Auth → Document → Process → Knowledge → Chat → Sources → Escalate → Assign → Resolve → Close → Audit
 */
test.describe("Complete business journey", () => {
  test("Docs → Knowledge → Chat → Ticket → Audit", async ({ asSuperAdmin, env }) => {
    test.setTimeout(300_000);
    const page = asSuperAdmin;
    const marker = `Journey-${uniqueSuffix()}`;
    const auth = JSON.parse(fs.readFileSync(storageStatePath(env, "superAdmin"), "utf8")) as {
      userId: number;
    };

    // Documents
    await page.goto("/app/documents");
    await page.locator('input[type="file"]').setInputFiles({
      name: `${marker}.txt`,
      mimeType: "text/plain",
      buffer: Buffer.from(
        `${marker}\n\nTo reset your password, visit Account Settings and click Forgot Password.\nNever share passwords with agents.\n`,
      ),
    });
    await expect(page.getByText(/document uploaded/i).first()).toBeVisible({ timeout: 30_000 });
    await page.getByPlaceholder(/search current page/i).fill(marker);
    const row = page.locator("tr", { hasText: marker }).first();
    await row.getByRole("button", { name: "Process" }).click();
    await expect
      .poll(
        async () => {
          await page.reload();
          await page.getByPlaceholder(/search current page/i).fill(marker);
          return page.locator("tr", { hasText: marker }).first().locator("td").nth(1).innerText();
        },
        { timeout: 120_000, intervals: [2_000, 4_000, 5_000] },
      )
      .toContain("COMPLETED");

    // Knowledge
    await page.goto("/app/knowledge");
    await page.getByLabel(/query/i).fill("How do I reset my password?");
    await page.getByRole("button", { name: /^search$/i }).click();
    await expect(page.getByText(/password|forgot/i).first()).toBeVisible({ timeout: 30_000 });

    // Chat + sources
    await page.goto("/app/chat");
    await page.getByRole("button", { name: "New conversation", exact: true }).click();
    await expect(page).toHaveURL(/conversation=\d+/);
    const question = "According to the policy, how do I reset my password?";
    await page.getByPlaceholder(/type your message/i).fill(question);
    await page.getByRole("button", { name: /^send$/i }).click();
    await expect(page.locator("main").getByText(question).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.locator("main").getByText(/Sources|password|Account Settings|knowledge/i).first()).toBeVisible({
      timeout: 90_000,
    });

    // Escalate
    const ticketSubject = `Journey ticket ${marker}`;
    await page.getByRole("button", { name: /escalate to ticket/i }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel(/^subject$/i).fill(ticketSubject);
    await dialog.getByLabel(/^description$/i).fill("Escalated during journey E2E");
    await dialog.getByRole("button", { name: /^escalate$/i }).click();
    await expect(page.getByText(/ticket .* created|SUP-/i).first()).toBeVisible({ timeout: 30_000 });

    await page.goto("/app/tickets");
    await page.getByRole("link", { name: ticketSubject }).click();
    await expect(page).toHaveURL(/\/app\/tickets\/\d+/);

    await page.getByPlaceholder(/user id/i).fill(String(auth.userId));
    await page.getByRole("button", { name: /^assign$/i }).click();
    await expect(page.getByText("IN_PROGRESS").first()).toBeVisible({ timeout: 20_000 });
    await page.getByRole("button", { name: /^resolve$/i }).click();
    await expect(page.getByText("RESOLVED").first()).toBeVisible({ timeout: 20_000 });
    page.once("dialog", (d) => d.accept());
    await page.getByRole("button", { name: /^close$/i }).click();
    await expect(page.getByText("CLOSED").first()).toBeVisible({ timeout: 20_000 });

    // Audit
    await page.goto("/app/audit");
    await page.getByLabel(/^action$/i).fill("tickets.close");
    await expect(page.getByRole("row").filter({ hasText: "tickets.close" }).first()).toBeVisible({
      timeout: 20_000,
    });
  });
});
