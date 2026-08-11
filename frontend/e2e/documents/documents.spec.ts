import { test, expect, uniqueSuffix } from "../fixtures/test";

test.describe("Documents lifecycle", () => {
  test("upload → process → COMPLETED → reindex → delete → restore", async ({
    asSuperAdmin,
  }) => {
    const page = asSuperAdmin;
    const marker = `E2E Doc ${uniqueSuffix()}`;

    await page.goto("/app/documents");
    await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: `${marker}.txt`,
      mimeType: "text/plain",
      buffer: Buffer.from(
        `Password Reset Policy ${marker}\n\nTo reset your password, open Account Settings and click Forgot Password.\n`,
      ),
    });

    await expect(page.getByText(/document uploaded/i).first()).toBeVisible({ timeout: 30_000 });
    await page.getByPlaceholder(/search current page/i).fill(marker);
    const row = page.locator("tr", { hasText: marker }).first();
    await expect(row).toBeVisible({ timeout: 30_000 });

    await row.getByRole("button", { name: "Process" }).click();
    await expect(page.getByText(/queued for processing|processing/i).first()).toBeVisible({
      timeout: 15_000,
    });

    await expect
      .poll(
        async () => {
          await page.reload();
          await page.getByPlaceholder(/search current page/i).fill(marker);
          const status = await page
            .locator("tr", { hasText: marker })
            .first()
            .locator("td")
            .nth(1)
            .innerText();
          return status.trim();
        },
        { timeout: 120_000, intervals: [2_000, 3_000, 5_000] },
      )
      .toBe("COMPLETED");

    const completedRow = page.locator("tr", { hasText: marker }).first();
    await expect(completedRow.locator("td").nth(3)).not.toHaveText("0");

    await completedRow.getByRole("button", { name: "Reindex" }).click();
    await expect(page.getByText(/reindex queued/i).first()).toBeVisible({ timeout: 20_000 });

    page.once("dialog", (dialog) => dialog.accept());
    await completedRow.getByRole("button", { name: "Delete" }).click();
    await expect(page.getByText(/document deleted/i).first()).toBeVisible({ timeout: 20_000 });

    await page.getByLabel(/include deleted/i).check();
    await page.getByPlaceholder(/search current page/i).fill(marker);
    const deletedRow = page.locator("tr", { hasText: marker }).first();
    await expect(deletedRow.getByRole("button", { name: "Restore" })).toBeVisible();
    await deletedRow.getByRole("button", { name: "Restore" }).click();
    await expect(page.getByText(/document restored/i).first()).toBeVisible({ timeout: 20_000 });
  });

  test("rejects unsupported extension via UI feedback or stuck list", async ({ asSuperAdmin }) => {
    const page = asSuperAdmin;
    await page.goto("/app/documents");
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "malware.exe",
      mimeType: "application/octet-stream",
      buffer: Buffer.from("MZ"),
    });
    await expect(
      page.getByText(/invalid|unsupported|failed|mime|extension|validation/i).first(),
    ).toBeVisible({ timeout: 20_000 });
  });

  test("rejects empty file upload", async ({ asSuperAdmin }) => {
    const page = asSuperAdmin;
    const marker = `E2E Empty ${uniqueSuffix()}`;
    await page.goto("/app/documents");
    await page.locator('input[type="file"]').setInputFiles({
      name: `${marker}.txt`,
      mimeType: "text/plain",
      buffer: Buffer.alloc(0),
    });
    await expect(page.getByText(/empty|invalid|failed|validation/i).first()).toBeVisible({
      timeout: 20_000,
    });
    await page.getByPlaceholder(/search current page/i).fill(marker);
    await expect(page.locator("tr", { hasText: marker })).toHaveCount(0);
  });

  test("rejects oversized upload for FREE plan (10 MB limit)", async ({ asFreePlanAdmin }) => {
    const page = asFreePlanAdmin;
    const marker = `E2E Big ${uniqueSuffix()}`;
    // FREE plan limit is 10 MiB; send 11 MiB so backend validate_file_size rejects it.
    const oversized = Buffer.alloc(11 * 1024 * 1024, 0x61);

    await page.goto("/app/documents");
    await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
    await page.locator('input[type="file"]').setInputFiles({
      name: `${marker}.txt`,
      mimeType: "text/plain",
      buffer: oversized,
    });
    await expect(
      page.getByText(/exceeds|limit|too large|file size|failed|validation/i).first(),
    ).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/document uploaded/i)).toHaveCount(0);
    await page.getByPlaceholder(/search current page/i).fill(marker);
    await expect(page.locator("tr", { hasText: marker })).toHaveCount(0);
  });
});
