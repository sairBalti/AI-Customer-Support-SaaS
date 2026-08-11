import { http, unwrapData } from "@/api/client";
import type { ManagedUser, Page } from "@/types/api";

export async function listUsers(params?: Record<string, unknown>) {
  const { data } = await http.get("/api/v1/users", { params });
  return unwrapData<Page<ManagedUser>>(data);
}

export async function getUser(userId: number) {
  const { data } = await http.get(`/api/v1/users/${userId}`);
  return unwrapData<ManagedUser>(data);
}

export async function createUser(payload: Record<string, unknown>) {
  const { data } = await http.post("/api/v1/users", payload);
  return unwrapData<ManagedUser>(data);
}

export async function updateUser(userId: number, payload: Record<string, unknown>) {
  const { data } = await http.patch(`/api/v1/users/${userId}`, payload);
  return unwrapData<ManagedUser>(data);
}

export async function softDeleteUser(userId: number) {
  const { data } = await http.delete(`/api/v1/users/${userId}`);
  return unwrapData<ManagedUser>(data);
}

export async function activateUser(userId: number) {
  const { data } = await http.patch(`/api/v1/users/${userId}/activate`);
  return unwrapData<ManagedUser>(data);
}

export async function deactivateUser(userId: number) {
  const { data } = await http.patch(`/api/v1/users/${userId}/deactivate`);
  return unwrapData<ManagedUser>(data);
}

export async function assignUserRole(userId: number, payload: { role_id?: number; role_name?: string }) {
  const { data } = await http.patch(`/api/v1/users/${userId}/roles`, payload);
  return unwrapData<ManagedUser>(data);
}
