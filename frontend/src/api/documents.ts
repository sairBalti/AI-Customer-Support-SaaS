import { http, unwrapData } from "@/api/client";
import type { Document, Page, StorageUsage } from "@/types/api";

export async function listDocuments(params?: Record<string, unknown>) {
  const { data } = await http.get("/api/v1/documents", { params });
  return unwrapData<Page<Document>>(data);
}

export async function getDocument(documentId: number) {
  const { data } = await http.get(`/api/v1/documents/${documentId}`);
  return unwrapData<Document>(data);
}

export async function getStorageUsage(companyId?: number) {
  const { data } = await http.get("/api/v1/documents/storage", {
    params: companyId ? { company_id: companyId } : undefined,
  });
  return unwrapData<StorageUsage>(data);
}

export async function uploadDocument(form: FormData, onUploadProgress?: (pct: number) => void) {
  const { data } = await http.post("/api/v1/documents", form, {
    onUploadProgress: (e) => {
      if (!onUploadProgress || !e.total) return;
      onUploadProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return unwrapData<Document>(data);
}

export async function updateDocument(documentId: number, payload: Record<string, unknown>) {
  const { data } = await http.patch(`/api/v1/documents/${documentId}`, payload);
  return unwrapData<Document>(data);
}

export async function deleteDocument(documentId: number) {
  const { data } = await http.delete(`/api/v1/documents/${documentId}`);
  return unwrapData<Document>(data);
}

export async function restoreDocument(documentId: number) {
  const { data } = await http.post(`/api/v1/documents/${documentId}/restore`);
  return unwrapData<Document>(data);
}

export async function processDocument(documentId: number) {
  const { data } = await http.post(`/api/v1/documents/${documentId}/process`);
  return unwrapData<Document>(data);
}

export async function reindexDocument(documentId: number) {
  const { data } = await http.post(`/api/v1/documents/${documentId}/reindex`);
  return unwrapData<Document>(data);
}
