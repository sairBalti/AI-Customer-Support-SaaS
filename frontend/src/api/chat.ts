import { http, unwrapData } from "@/api/client";
import type { ChatAnswer, ChatMessage, ChatSession, Ticket } from "@/types/api";

export async function listConversations(params?: { limit?: number; offset?: number }) {
  const { data } = await http.get("/api/v1/chat/conversations", { params });
  return unwrapData<{ items: ChatSession[] }>(data);
}

export async function createConversation(payload?: { title?: string; language?: string }) {
  const { data } = await http.post("/api/v1/chat/conversations", payload ?? {});
  return unwrapData<ChatSession>(data);
}

export async function getConversation(conversationId: number) {
  const { data } = await http.get(`/api/v1/chat/conversations/${conversationId}`);
  return unwrapData<{ conversation: ChatSession; messages: ChatMessage[] }>(data);
}

export async function sendMessage(conversationId: number, content: string) {
  const { data } = await http.post(`/api/v1/chat/conversations/${conversationId}/messages`, {
    content,
  });
  return unwrapData<ChatAnswer>(data);
}

export async function escalateConversation(
  conversationId: number,
  payload: Record<string, unknown>,
) {
  const { data } = await http.post(
    `/api/v1/chat/conversations/${conversationId}/ticket`,
    payload,
  );
  return unwrapData<Ticket>(data);
}
