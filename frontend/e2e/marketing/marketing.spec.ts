import { test, expect } from "../fixtures/test";

test.describe("Marketing site", () => {
  test("landing page shows product pitch and CTAs", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", {
        name: /customer support that answers with your knowledge/i,
      }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /register your company/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /sign in to workspace/i })).toBeVisible();
    await expect(page.locator("#features")).toBeVisible();
    await expect(page.locator("#pricing")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Pro" })).toBeVisible();
  });

  test("marketing CTAs reach auth pages", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /^start free$/i }).click();
    await expect(page).toHaveURL(/\/register/);
    await expect(page.getByRole("heading", { name: /register company/i })).toBeVisible();

    await page.goto("/");
    await page.getByRole("banner").getByRole("link", { name: /^sign in$/i }).click();
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  });
});
