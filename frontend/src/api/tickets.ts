import { http, unwrapData } from "@/api/client";
import type { Page, Ticket } from "@/types/api";

export async function listTickets(params?: Record<string, unknown>) {
  const { data } = await http.get("/api/v1/tickets", { params });
  return unwrapData<Page<Ticket>>(data);
}

export async function getTicket(ticketId: number) {
  const { data } = await http.get(`/api/v1/tickets/${ticketId}`);
  return unwrapData<Ticket>(data);
}

export async function createTicket(payload: Record<string, unknown>) {
  const { data } = await http.post("/api/v1/tickets", payload);
  return unwrapData<Ticket>(data);
}

export async function updateTicket(ticketId: number, payload: Record<string, unknown>) {
  const { data } = await http.patch(`/api/v1/tickets/${ticketId}`, payload);
  return unwrapData<Ticket>(data);
}

export async function assignTicket(ticketId: number, assignedTo: number) {
  const { data } = await http.post(`/api/v1/tickets/${ticketId}/assign`, {
    assigned_to: assignedTo,
  });
  return unwrapData<Ticket>(data);
}

export async function resolveTicket(ticketId: number) {
  const { data } = await http.post(`/api/v1/tickets/${ticketId}/resolve`);
  return unwrapData<Ticket>(data);
}

export async function closeTicket(ticketId: number) {
  const { data } = await http.post(`/api/v1/tickets/${ticketId}/close`);
  return unwrapData<Ticket>(data);
}
