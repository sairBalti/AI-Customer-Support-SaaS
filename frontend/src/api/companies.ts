import { http, unwrapData } from "@/api/client";
import type { Company, Page } from "@/types/api";

export async function listCompanies(params?: Record<string, unknown>) {
  const { data } = await http.get("/api/v1/companies", { params });
  return unwrapData<Page<Company>>(data);
}

export async function createCompany(payload: Record<string, unknown>) {
  const { data } = await http.post("/api/v1/companies", payload);
  return unwrapData<Company>(data);
}

export async function getCompany(companyId: number) {
  const { data } = await http.get(`/api/v1/companies/${companyId}`);
  return unwrapData<Company>(data);
}

export async function updateCompany(companyId: number, payload: Record<string, unknown>) {
  const { data } = await http.put(`/api/v1/companies/${companyId}`, payload);
  return unwrapData<Company>(data);
}

export async function updateCompanyStatus(companyId: number, status: string) {
  const { data } = await http.patch(`/api/v1/companies/${companyId}/status`, { status });
  return unwrapData<Company>(data);
}

export async function updateCompanySubscription(companyId: number, payload: Record<string, unknown>) {
  const { data } = await http.patch(`/api/v1/companies/${companyId}/subscription`, payload);
  return unwrapData<Company>(data);
}

export async function deleteCompany(companyId: number) {
  const { data } = await http.delete(`/api/v1/companies/${companyId}`);
  return unwrapData<Company>(data);
}
