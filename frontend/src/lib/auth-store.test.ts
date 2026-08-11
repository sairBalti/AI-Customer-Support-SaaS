import { beforeEach, describe, expect, it } from "vitest";
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  isAuthenticated,
  setSession,
} from "@/lib/auth-store";
import type { AuthUser, TokenPair } from "@/types/api";

const tokens: TokenPair = {
  access_token: "access-123",
  refresh_token: "refresh-456",
  token_type: "bearer",
  expires_in: 1800,
};

const user: AuthUser = {
  user_id: 1,
  company_id: 1,
  email: "sa@example.com",
  first_name: "Super",
  last_name: "Admin",
  display_name: "Super Admin",
  role_name: "SUPER_ADMIN",
  permissions: ["audit.read"],
  is_super_admin: true,
};

describe("auth-store", () => {
  beforeEach(() => {
    clearSession();
    sessionStorage.clear();
  });

  it("keeps access token in memory and refresh in sessionStorage", () => {
    setSession(tokens, user);
    expect(getAccessToken()).toBe("access-123");
    expect(getRefreshToken()).toBe("refresh-456");
    expect(isAuthenticated()).toBe(true);
  });

  it("clears both tokens on logout/clear", () => {
    setSession(tokens, user);
    clearSession();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });
});
