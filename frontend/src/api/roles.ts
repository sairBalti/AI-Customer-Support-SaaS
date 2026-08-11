import { http, unwrapData } from "@/api/client";
import type { Page, Role } from "@/types/api";

export async function listRoles(params?: Record<string, unknown>) {
  const { data } = await http.get("/api/v1/roles", { params });
  return unwrapData<Page<Role>>(data);
}

export async function getRole(roleId: number) {
  const { data } = await http.get(`/api/v1/roles/${roleId}`);
  return unwrapData<Role>(data);
}

export async function createRole(payload: Record<string, unknown>) {
  const { data } = await http.post("/api/v1/roles", payload);
  return unwrapData<Role>(data);
}

export async function updateRole(roleId: number, payload: Record<string, unknown>) {
  const { data } = await http.patch(`/api/v1/roles/${roleId}`, payload);
  return unwrapData<Role>(data);
}

export async function deleteRole(roleId: number) {
  const { data } = await http.delete(`/api/v1/roles/${roleId}`);
  return unwrapData<Role>(data);
}
