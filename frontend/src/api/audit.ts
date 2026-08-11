import { http, unwrapData } from "@/api/client";
import type { AuditLog, Page } from "@/types/api";

export async function listAuditLogs(params?: Record<string, unknown>) {
  const { data } = await http.get("/api/v1/audit-logs", { params });
  return unwrapData<Page<AuditLog>>(data);
}

export async function getAuditLog(auditLogId: number) {
  const { data } = await http.get(`/api/v1/audit-logs/${auditLogId}`);
  return unwrapData<AuditLog>(data);
}
