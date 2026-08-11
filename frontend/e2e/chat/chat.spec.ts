import { test, expect, uniqueSuffix } from "../fixtures/test";
import type { Page } from "@playwright/test";
import { apiLogin, ensureSeedUsers } from "../fixtures/api";
import { loadE2EEnv } from "../fixtures/env";

function createConversationCta(page: Page) {
  return page.getByRole("button", { name: "New conversation", exact: true });
}

async function ensureKnowledgeReady() {
  const env = loadE2EEnv();
  await ensureSeedUsers(env);
  const session = await apiLogin(env, env.users.superAdmin.email, env.users.superAdmin.password);
  const token = session.tokens.access_token;
  const marker = `E2E-Chat-KB-${uniqueSuffix()}`;
  const form = new FormData();
  form.append(
    "file",
    new Blob(
      [
        `${marker}\nTo reset your password, visit Account Settings and click Forgot Password.\n`,
      ],
      { type: "text/plain" },
    ),
    `${marker}.txt`,
  );
  form.append("document_name", marker);
  const uploadRes = await fetch(`${env.apiBaseUrl}/api/v1/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const upload = (await uploadRes.json()) as { data: { document_id: number } };
  const docId = upload.data.document_id;
  await fetch(`${env.apiBaseUrl}/api/v1/documents/${docId}/process`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: "{}",
  });
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    const g = await fetch(`${env.apiBaseUrl}/api/v1/documents/${docId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const body = (await g.json()) as { data: { processing_status: string } };
    if (body.data.processing_status === "COMPLETED") return marker;
    if (body.data.processing_status === "FAILED") throw new Error("kb process failed");
  }
  throw new Error("kb process timeout");
}

test.describe("Chat", () => {
  test("create conversation, ask RAG question, keep URL state", async ({ asSuperAdmin }) => {
    await ensureKnowledgeReady();
    const page = asSuperAdmin;
    await page.goto("/app/chat");
    await expect(page.getByRole("heading", { name: "Chat" })).toBeVisible();
    await createConversationCta(page).click();
    await expect(page).toHaveURL(/conversation=\d+/);

    const question = "How do I reset my password according to company policy?";
    await page.getByPlaceholder(/type your message/i).fill(question);
    await page.getByRole("button", { name: /^send$/i }).click();
    await expect(page.locator("main").getByText(question).first()).toBeVisible();
    await expect(page.locator("main").getByText(/^AI$/i).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.locator("main").getByText(/Sources|Doc #|Account Settings|password/i).first()).toBeVisible({
      timeout: 60_000,
    });

    const url = page.url();
    await page.reload();
    await expect(page).toHaveURL(url);
    await expect(page.locator("main").getByText(question).first()).toBeVisible({ timeout: 30_000 });

    await createConversationCta(page).click();
    await expect(page).toHaveURL(/conversation=\d+/);
    const secondUrl = page.url();
    expect(secondUrl).not.toBe(url);
  });

  test("Customer can start chat; Agent cannot create conversation", async ({
    asCustomer,
    asAgent,
  }) => {
    await asCustomer.goto("/app/chat");
    await expect(createConversationCta(asCustomer)).toBeVisible();

    await asAgent.goto("/app/chat");
    await expect(asAgent.getByRole("heading", { name: "Chat" })).toBeVisible();
    await expect(createConversationCta(asAgent)).toHaveCount(0);
  });
});

test.describe("Chat escalation", () => {
  test("escalate conversation to ticket and open it", async ({ asSuperAdmin }) => {
    const page = asSuperAdmin;
    await page.goto("/app/chat");
    await createConversationCta(page).click();
    await expect(page).toHaveURL(/conversation=\d+/);
    await page.getByPlaceholder(/type your message/i).fill("I need a human, escalation please.");
    await page.getByRole("button", { name: /^send$/i }).click();
    await expect(page.locator("main").getByText(/I need a human/i).first()).toBeVisible();
    await expect(page.locator("main").getByText(/^AI$/i).first()).toBeVisible({
      timeout: 60_000,
    });

    await page.getByRole("button", { name: /escalate to ticket/i }).click();
    const subject = `E2E escalate ${uniqueSuffix()}`;
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel(/^subject$/i).fill(subject);
    await dialog.getByLabel(/^description$/i).fill("Escalated from chat E2E");
    await dialog.getByRole("button", { name: /^escalate$/i }).click();
    await expect(page.getByText(/ticket .* created|SUP-/i).first()).toBeVisible({ timeout: 30_000 });

    await page.goto("/app/tickets");
    await expect(page.getByText(subject)).toBeVisible({ timeout: 20_000 });
    await page.getByRole("link", { name: subject }).click();
    await expect(page).toHaveURL(/\/app\/tickets\/\d+/);
  });
});
