import type { AuthUser, Permission } from "@/types/api";

export function can(user: AuthUser | null | undefined, ...permissions: Permission[]) {
  if (!user) return false;
  if (user.is_super_admin) return true;
  return permissions.every((p) => user.permissions.includes(p));
}

export function canAny(user: AuthUser | null | undefined, ...permissions: Permission[]) {
  if (!user) return false;
  if (user.is_super_admin) return true;
  return permissions.some((p) => user.permissions.includes(p));
}
