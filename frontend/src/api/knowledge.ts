import { http, unwrapData } from "@/api/client";
import type { KnowledgeHit } from "@/types/api";

export async function searchKnowledge(payload: {
  query: string;
  top_k?: number;
  document_id?: number;
  company_id?: number;
}) {
  const { data } = await http.post("/api/v1/knowledge/search", payload);
  return unwrapData<{ items: KnowledgeHit[] }>(data);
}
