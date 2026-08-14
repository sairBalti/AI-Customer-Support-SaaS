import { test, expect, uniqueSuffix } from "../fixtures/test";
import { apiLogin, ensureSeedUsers } from "../fixtures/api";
import { loadE2EEnv } from "../fixtures/env";

async function seedProcessedDocument(marker: string) {
  const env = loadE2EEnv();
  await ensureSeedUsers(env);
  const session = await apiLogin(env, env.users.superAdmin.email, env.users.superAdmin.password);
  const token = session.tokens.access_token;
  const form = new FormData();
  const blob = new Blob(
    [
      `Knowledge Fixture ${marker}\n\nTo reset your password, visit Account Settings and click Forgot Password.\nRefunds are processed within 7 business days.\n`,
    ],
    { type: "text/plain" },
  );
  form.append("file", blob, `${marker}.txt`);
  form.append("document_name", marker);

  const uploadRes = await fetch(`${env.apiBaseUrl}/api/v1/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const uploadJson = (await uploadRes.json()) as {
    success: boolean;
    data: { document_id: number; processing_status: string };
  };
  if (!uploadRes.ok || !uploadJson.success) {
    throw new Error(`upload failed: ${JSON.stringify(uploadJson)}`);
  }
  const docId = uploadJson.data.document_id;
  const procRes = await fetch(`${env.apiBaseUrl}/api/v1/documents/${docId}/process`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: "{}",
  });
  if (!procRes.ok) throw new Error(`process failed: ${await procRes.text()}`);

  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    const g = await fetch(`${env.apiBaseUrl}/api/v1/documents/${docId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const body = (await g.json()) as {
      data: { processing_status: string; total_chunks: number; original_filename: string };
    };
    if (body.data.processing_status === "COMPLETED") {
      return { docId, filename: body.data.original_filename, chunks: body.data.total_chunks };
    }
    if (body.data.processing_status === "FAILED") {
      throw new Error("document processing failed");
    }
  }
  throw new Error("document processing timed out");
}

test.describe("Knowledge search", () => {
  test("finds processed document chunks", async ({ asSuperAdmin }) => {
    const marker = `E2E-Know-${uniqueSuffix()}`;
    const seeded = await seedProcessedDocument(marker);
    expect(seeded.chunks).toBeGreaterThan(0);

    const page = asSuperAdmin;
    await page.goto("/app/knowledge");
    await expect(page.getByRole("heading", { name: /knowledge/i })).toBeVisible();
    await page.getByLabel(/query/i).fill("How do I reset my password?");
    await page.getByRole("button", { name: /^search$/i }).click();
    await expect(page.getByText(/password/i).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/%/).first()).toBeVisible();
  });

  test("empty query is validated", async ({ asSuperAdmin }) => {
    const page = asSuperAdmin;
    await page.goto("/app/knowledge");
    await expect(page.getByRole("heading", { name: /knowledge/i })).toBeVisible();
    await page.getByRole("button", { name: /^search$/i }).click();
    await expect(page.getByText(/enter a search query|required|min/i).first()).toBeVisible();
  });
});
