/** Shared API DTOs mirrored from FastAPI schemas. */

export type Permission =
  | "companies.read"
  | "companies.update"
  | "companies.manage"
  | "users.create"
  | "users.read"
  | "users.update"
  | "users.delete"
  | "roles.create"
  | "roles.read"
  | "roles.update"
  | "roles.delete"
  | "documents.upload"
  | "documents.read"
  | "documents.update"
  | "documents.delete"
  | "documents.reindex"
  | "knowledge.process"
  | "knowledge.search"
  | "chat.start"
  | "chat.read"
  | "tickets.create"
  | "tickets.read"
  | "tickets.update"
  | "tickets.assign"
  | "tickets.resolve"
  | "tickets.close"
  | "audit.read"
  | (string & {});

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthUser {
  user_id: number;
  company_id: number;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string | null;
  role_name: string;
  permissions: Permission[];
  is_super_admin: boolean;
}

export interface AuthSession {
  tokens: TokenPair;
  user: AuthUser;
}

export interface PageMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface Page<T> {
  items: T[];
  meta: PageMeta;
}

export interface Company {
  company_id: number;
  company_name: string;
  company_slug: string;
  email: string;
  legal_name: string | null;
  phone: string | null;
  website: string | null;
  logo_url: string | null;
  industry: string | null;
  country: string | null;
  timezone: string;
  subscription_plan: string;
  status: string;
  max_users: number;
  max_documents: number;
  max_storage_mb: number;
  monthly_ai_tokens: number;
  token_usage: number;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface ManagedUser {
  user_id: number;
  company_id: number;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string | null;
  role_id: number | null;
  role_name: string | null;
  status: string;
  is_email_verified: boolean;
  must_change_password: boolean;
  phone: string | null;
  job_title: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Role {
  role_id: number;
  role_name: string;
  display_name: string;
  description: string | null;
  company_id: number | null;
  is_system_role: boolean;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Document {
  document_id: number;
  company_id: number;
  document_name: string;
  original_filename: string;
  description: string | null;
  mime_type: string | null;
  file_size_bytes: number;
  processing_status: string;
  language: string;
  tags: string[];
  total_chunks: number;
  uploaded_by: number | null;
  storage_provider: string;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface StorageUsage {
  company_id: number;
  document_count: number;
  used_bytes: number;
  max_documents: number;
  max_storage_bytes: number;
  remaining_documents: number;
  remaining_bytes: number;
}

export interface KnowledgeHit {
  document_id: number;
  chunk_id: number | null;
  chunk_uuid: string;
  content: string;
  score: number;
  chunk_index: number;
  source_filename: string | null;
  page_number: number | null;
  metadata: Record<string, unknown>;
}

export interface ChatSession {
  conversation_id: number;
  conversation_uuid?: string;
  company_id: number;
  customer_id: number;
  title: string | null;
  status: string;
  language: string;
  total_messages?: number;
  ai_provider?: string;
  ai_model?: string;
  last_message_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  message_id: number;
  message_uuid?: string;
  conversation_id: number;
  company_id: number;
  sender_type: string;
  message_type: string;
  content: string;
  citations?: ChatSource[] | Record<string, unknown>[];
  ai_provider?: string | null;
  ai_model?: string | null;
  created_at: string;
}

export interface ChatSource {
  document_id: number;
  document_name: string;
  chunk_id: number | null;
  chunk_uuid?: string | null;
  page: number | null;
  score: number;
}

export interface ChatAnswer {
  answer: string;
  sources: ChatSource[];
  used_knowledge: boolean;
  conversation: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export interface Ticket {
  ticket_id: number;
  company_id: number;
  customer_id: number;
  ticket_number: string;
  subject: string;
  description: string;
  priority: string;
  status: string;
  category: string;
  source: string;
  conversation_id: number | null;
  assigned_to: number | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface AuditLog {
  audit_log_id: number;
  company_id: number;
  actor_user_id: number | null;
  audit_uuid: string | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  description: string | null;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}
