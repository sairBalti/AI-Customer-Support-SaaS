import { test, expect, expectNavVisible, expectNavHidden, uniqueSuffix } from "../fixtures/test";

test.describe("Users / RBAC navigation", () => {
  test("Super Admin sees platform admin modules", async ({ asSuperAdmin }) => {
    await asSuperAdmin.goto("/app");
    await expectNavVisible(asSuperAdmin, "Companies");
    await expectNavVisible(asSuperAdmin, "Users");
    await expectNavVisible(asSuperAdmin, "Roles");
    await expectNavVisible(asSuperAdmin, "Documents");
    await expectNavVisible(asSuperAdmin, "Audit");
    await expectNavVisible(asSuperAdmin, "Tickets");
    await asSuperAdmin.goto("/app/documents");
    await expect(asSuperAdmin.getByText(/drag and drop a file/i)).toBeVisible();
    await asSuperAdmin.goto("/app/tickets");
    await expect(asSuperAdmin.getByRole("button", { name: /create ticket/i })).toBeVisible();
  });

  test("Company Admin sees admin modules", async ({ asCompanyAdmin }) => {
    await asCompanyAdmin.goto("/app");
    await expectNavVisible(asCompanyAdmin, "Users");
    await expectNavVisible(asCompanyAdmin, "Documents");
    await expectNavVisible(asCompanyAdmin, "Audit");
    await expectNavHidden(asCompanyAdmin, "Roles");
    await asCompanyAdmin.goto("/app/users");
    await expect(asCompanyAdmin.getByRole("heading", { name: "Users" })).toBeVisible();
    await expect(asCompanyAdmin.getByRole("button", { name: /create user/i })).toBeVisible();
    await asCompanyAdmin.goto("/app/roles");
    await expect(asCompanyAdmin).toHaveURL(/\/forbidden/);
    await asCompanyAdmin.goto("/app/documents");
    await expect(asCompanyAdmin.getByText(/drag and drop a file/i)).toBeVisible();
  });

  test("Support Manager sees tickets/audit but not user admin create necessarily", async ({
    asSupportManager,
  }) => {
    await asSupportManager.goto("/app");
    await expectNavVisible(asSupportManager, "Documents");
    await expectNavVisible(asSupportManager, "Tickets");
    await expectNavVisible(asSupportManager, "Audit");
    await expectNavHidden(asSupportManager, "Users");
    await asSupportManager.goto("/app/users");
    await expect(asSupportManager).toHaveURL(/\/forbidden/);
    await asSupportManager.goto("/app/documents");
    await expect(asSupportManager.getByText(/drag and drop a file/i)).toBeVisible();
    await asSupportManager.goto("/app/tickets");
    await expect(asSupportManager.getByRole("button", { name: /create ticket/i })).toBeVisible();
  });

  test("Agent hides audit and document upload; no assign on tickets", async ({ asAgent }) => {
    await asAgent.goto("/app");
    await expectNavVisible(asAgent, "Documents");
    await expectNavVisible(asAgent, "Tickets");
    await expectNavHidden(asAgent, "Audit");
    await expectNavHidden(asAgent, "Users");
    await asAgent.goto("/app/documents");
    await expect(asAgent.getByRole("heading", { name: "Documents" })).toBeVisible();
    await expect(asAgent.getByText(/drag and drop a file/i)).toHaveCount(0);
    await asAgent.goto("/app/audit");
    await expect(asAgent).toHaveURL(/\/forbidden/);

    await asAgent.goto("/app/tickets");
    const subject = `E2E Agent Ticket ${uniqueSuffix()}`;
    await asAgent.getByRole("button", { name: /create ticket/i }).click();
    const dialog = asAgent.getByRole("dialog");
    await dialog.getByLabel(/^subject$/i).fill(subject);
    await dialog.getByLabel(/^description$/i).fill("Agent ticket visibility check");
    await dialog.getByRole("button", { name: /^create$/i }).click();
    await asAgent.getByRole("link", { name: subject }).click();
    await expect(asAgent.getByRole("button", { name: /^assign$/i })).toHaveCount(0);
  });

  test("Customer cannot access admin modules via URL", async ({ asCustomer }) => {
    await asCustomer.goto("/app");
    await expectNavVisible(asCustomer, "Chat");
    await expectNavVisible(asCustomer, "Tickets");
    await expectNavHidden(asCustomer, "Documents");
    await expectNavHidden(asCustomer, "Audit");
    await expectNavHidden(asCustomer, "Companies");
    for (const route of ["/app/companies", "/app/users", "/app/documents", "/app/audit"]) {
      await asCustomer.goto(route);
      await expect(asCustomer).toHaveURL(/\/(forbidden|login)/);
      if (asCustomer.url().includes("/login")) {
        throw new Error(`Customer session lost navigating to ${route}`);
      }
      await expect(asCustomer).toHaveURL(/\/forbidden/);
    }
  });
});
