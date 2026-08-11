import { describe, expect, it } from "vitest";
import { can, canAny } from "@/lib/permissions";
import type { AuthUser } from "@/types/api";

const baseUser = (overrides: Partial<AuthUser> = {}): AuthUser => ({
  user_id: 1,
  company_id: 1,
  email: "u@example.com",
  first_name: "Test",
  last_name: "User",
  display_name: "Test User",
  role_name: "SUPPORT_AGENT",
  permissions: ["documents.read", "tickets.read", "chat.read"],
  is_super_admin: false,
  ...overrides,
});

describe("permissions", () => {
  it("denies when user is missing", () => {
    expect(can(null, "audit.read")).toBe(false);
    expect(canAny(undefined, "chat.start")).toBe(false);
  });

  it("grants everything to super admin", () => {
    const user = baseUser({ is_super_admin: true, permissions: [] });
    expect(can(user, "audit.read")).toBe(true);
    expect(canAny(user, "chat.start")).toBe(true);
  });

  it("requires all permissions for can()", () => {
    const user = baseUser();
    expect(can(user, "documents.read")).toBe(true);
    expect(can(user, "documents.read", "documents.upload")).toBe(false);
  });

  it("requires any permission for canAny()", () => {
    const user = baseUser();
    expect(canAny(user, "chat.start", "chat.read")).toBe(true);
    expect(canAny(user, "chat.start", "audit.read")).toBe(false);
  });
});
