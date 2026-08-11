import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { login } from "@/api/auth";
import { listDocuments } from "@/api/documents";
import { ApiError } from "@/lib/api-error";
import { clearSession, setAccessToken } from "@/lib/auth-store";

const server = setupServer(
  http.post("/api/v1/auth/login", async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.email !== "ok@example.com") {
      return HttpResponse.json(
        { success: false, error: { code: "INVALID_CREDENTIALS", message: "Bad creds" } },
        { status: 401 },
      );
    }
    return HttpResponse.json({
      success: true,
      data: {
        tokens: {
          access_token: "a",
          refresh_token: "r",
          token_type: "bearer",
          expires_in: 1800,
        },
        user: {
          user_id: 1,
          company_id: 1,
          email: body.email,
          first_name: "Ok",
          last_name: "User",
          display_name: "Ok User",
          role_name: "COMPANY_ADMIN",
          permissions: ["documents.read"],
          is_super_admin: false,
        },
      },
      message: "Login successful.",
    });
  }),
  http.get("/api/v1/documents", () =>
    HttpResponse.json({
      success: true,
      data: {
        items: [],
        meta: { page: 1, page_size: 20, total_items: 0, total_pages: 0 },
      },
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  clearSession();
});
afterAll(() => server.close());

describe("api clients (msw)", () => {
  it("logs in against the envelope contract", async () => {
    const session = await login("ok@example.com", "Str0ng!Password");
    expect(session.tokens.access_token).toBe("a");
    expect(session.user.email).toBe("ok@example.com");
  });

  it("maps API errors", async () => {
    await expect(login("bad@example.com", "x")).rejects.toBeInstanceOf(ApiError);
  });

  it("lists documents with bearer token", async () => {
    setAccessToken("a");
    const page = await listDocuments({ page: 1, page_size: 20 });
    expect(page.items).toEqual([]);
    expect(page.meta.total_items).toBe(0);
  });
});
