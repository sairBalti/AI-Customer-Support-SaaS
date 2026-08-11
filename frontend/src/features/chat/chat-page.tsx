import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  createConversation,
  escalateConversation,
  getConversation,
  listConversations,
  sendMessage,
} from "@/api/chat";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";
import { cn, formatDate } from "@/lib/utils";
import type { ChatMessage, ChatSource } from "@/types/api";

const messageSchema = z.object({
  content: z.string().min(1, "Message cannot be empty"),
});

const escalateSchema = z.object({
  subject: z.string().min(1),
  description: z.string().min(1),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "URGENT"]),
  category: z.enum(["GENERAL", "TECHNICAL", "BILLING", "ACCOUNT", "OTHER"]),
});

type MessageValues = z.infer<typeof messageSchema>;
type EscalateValues = z.infer<typeof escalateSchema>;

function isAssistant(senderType: string) {
  return senderType === "AI" || senderType === "AGENT";
}

function asSources(raw: unknown): ChatSource[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      const s = item as Record<string, unknown>;
      const documentId = Number(s.document_id);
      return {
        document_id: documentId,
        document_name: String(
          s.document_name ?? s.source_filename ?? `Doc #${s.document_id}`,
        ),
        chunk_id: s.chunk_id == null ? null : Number(s.chunk_id),
        chunk_uuid: (s.chunk_uuid as string | null | undefined) ?? null,
        page: (s.page as number | null | undefined) ?? (s.page_number as number | null | undefined) ?? null,
        score: Number(s.score ?? 0),
      };
    })
    .filter((s) => Number.isFinite(s.document_id));
}

export function ChatPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [messageSources, setMessageSources] = useState<Record<number, ChatSource[]>>({});
  const [escalateOpen, setEscalateOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const selectedId = useMemo(() => {
    const raw = searchParams.get("conversation");
    const id = raw ? Number(raw) : NaN;
    return Number.isFinite(id) ? id : null;
  }, [searchParams]);

  const conversationsQuery = useQuery({
    queryKey: ["chat", "conversations"],
    queryFn: () => listConversations({ limit: 50, offset: 0 }),
  });

  const conversationQuery = useQuery({
    queryKey: ["chat", "conversation", selectedId],
    queryFn: () => getConversation(selectedId!),
    enabled: selectedId !== null,
  });

  useEffect(() => {
    if (selectedId !== null || !conversationsQuery.data?.items.length) return;
    const first = conversationsQuery.data.items[0]!.conversation_id;
    setSearchParams({ conversation: String(first) }, { replace: true });
  }, [conversationsQuery.data, selectedId, setSearchParams]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversationQuery.data?.messages, messageSources]);

  const createMutation = useMutation({
    mutationFn: () => createConversation({ title: "New conversation" }),
    onSuccess: (session) => {
      toast.success("Conversation created");
      void qc.invalidateQueries({ queryKey: ["chat", "conversations"] });
      setSearchParams({ conversation: String(session.conversation_id) });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const messageForm = useForm<MessageValues>({
    resolver: zodResolver(messageSchema),
    defaultValues: { content: "" },
  });

  const sendMutation = useMutation({
    mutationFn: (values: MessageValues) => sendMessage(selectedId!, values.content),
    onSuccess: (answer) => {
      messageForm.reset();
      setMessageSources((prev) => ({
        ...prev,
        [answer.assistant_message.message_id]: asSources(answer.sources),
      }));
      qc.setQueryData(
        ["chat", "conversation", selectedId],
        (old: { conversation: typeof answer.conversation; messages: ChatMessage[] } | undefined) => {
          if (!old) {
            return {
              conversation: answer.conversation,
              messages: [answer.user_message, answer.assistant_message],
            };
          }
          return {
            conversation: answer.conversation,
            messages: [...old.messages, answer.user_message, answer.assistant_message],
          };
        },
      );
      void qc.invalidateQueries({ queryKey: ["chat", "conversations"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const escalateForm = useForm<EscalateValues>({
    resolver: zodResolver(escalateSchema),
    defaultValues: {
      subject: "",
      description: "",
      priority: "MEDIUM",
      category: "GENERAL",
    },
  });

  const escalateMutation = useMutation({
    mutationFn: (values: EscalateValues) => escalateConversation(selectedId!, values),
    onSuccess: (ticket) => {
      const path = `/app/tickets/${ticket.ticket_id}`;
      toast.success(
        <span>
          Ticket{" "}
          <Link className="underline font-medium" to={path}>
            {ticket.ticket_number}
          </Link>{" "}
          created
        </span>,
        {
          action: {
            label: "View",
            onClick: () => navigate(path),
          },
        },
      );
      setEscalateOpen(false);
      escalateForm.reset();
      void qc.invalidateQueries({ queryKey: ["tickets"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const conversations = conversationsQuery.data?.items ?? [];
  const messages = conversationQuery.data?.messages ?? [];
  const activeConversation = conversationQuery.data?.conversation;
  const canStartChat = can("chat.start");
  const canCreateTicket = can("tickets.create");

  return (
    <div className="flex h-[calc(100vh-8rem)] min-h-[32rem] flex-col">
      <PageHeader
        title="Chat"
        description="Customer support conversations with AI assistance."
        actions={
          canStartChat ? (
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              New conversation
            </Button>
          ) : null
        }
      />

      <div className="flex min-h-0 flex-1 gap-4">
        <aside className="flex w-64 shrink-0 flex-col rounded-lg border border-border bg-card">
          <div className="border-b border-border px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Conversations
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {conversationsQuery.isLoading ? <LoadingBlock label="Loading…" /> : null}
            {conversationsQuery.error ? (
              <ErrorBlock message={getErrorMessage(conversationsQuery.error)} />
            ) : null}
            {conversations.length === 0 && !conversationsQuery.isLoading ? (
              <p className="px-2 py-4 text-center text-xs text-muted-foreground">No conversations yet</p>
            ) : null}
            {conversations.map((session) => (
              <button
                key={session.conversation_id}
                type="button"
                className={cn(
                  "mb-1 w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-muted",
                  selectedId === session.conversation_id && "bg-accent text-accent-foreground",
                )}
                onClick={() =>
                  setSearchParams({ conversation: String(session.conversation_id) })
                }
              >
                <div className="truncate font-medium">
                  {session.title ?? `Conversation #${session.conversation_id}`}
                </div>
                <div className="truncate text-xs text-muted-foreground">
                  {formatDate(session.updated_at)}
                </div>
              </button>
            ))}
          </div>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col rounded-lg border border-border bg-card">
          {!selectedId ? (
            <EmptyState
              title="Select a conversation"
              description="Choose one from the list or start a new conversation."
              className="m-4 border-0"
            />
          ) : conversationQuery.isLoading ? (
            <LoadingBlock />
          ) : conversationQuery.error ? (
            <ErrorBlock message={getErrorMessage(conversationQuery.error)} />
          ) : (
            <>
              <div className="flex items-center justify-between border-b border-border px-4 py-3">
                <div>
                  <div className="font-medium">
                    {activeConversation?.title ?? `Conversation #${selectedId}`}
                  </div>
                  {activeConversation ? (
                    <div className="text-xs text-muted-foreground">
                      Status {activeConversation.status} · {formatDate(activeConversation.updated_at)}
                    </div>
                  ) : null}
                </div>
                {canCreateTicket ? (
                  <Dialog open={escalateOpen} onOpenChange={setEscalateOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" variant="outline">
                        Escalate to ticket
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Escalate conversation</DialogTitle>
                        <DialogDescription>
                          Create a support ticket from this conversation.
                        </DialogDescription>
                      </DialogHeader>
                      <form
                        className="space-y-3"
                        onSubmit={escalateForm.handleSubmit((values) =>
                          escalateMutation.mutate(values),
                        )}
                      >
                      <div className="space-y-1">
                        <Label htmlFor="escalate-subject">Subject</Label>
                        <Input id="escalate-subject" {...escalateForm.register("subject")} />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="escalate-description">Description</Label>
                        <Textarea
                          id="escalate-description"
                          rows={4}
                          {...escalateForm.register("description")}
                        />
                      </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-1">
                            <Label>Priority</Label>
                            <select
                              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                              {...escalateForm.register("priority")}
                            >
                              <option value="LOW">LOW</option>
                              <option value="MEDIUM">MEDIUM</option>
                              <option value="HIGH">HIGH</option>
                              <option value="URGENT">URGENT</option>
                            </select>
                          </div>
                          <div className="space-y-1">
                            <Label>Category</Label>
                            <select
                              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                              {...escalateForm.register("category")}
                            >
                              <option value="GENERAL">GENERAL</option>
                              <option value="TECHNICAL">TECHNICAL</option>
                              <option value="BILLING">BILLING</option>
                              <option value="ACCOUNT">ACCOUNT</option>
                              <option value="OTHER">OTHER</option>
                            </select>
                          </div>
                        </div>
                        <Button type="submit" disabled={escalateMutation.isPending}>
                          Escalate
                        </Button>
                      </form>
                    </DialogContent>
                  </Dialog>
                ) : null}
              </div>

              <div className="flex-1 space-y-4 overflow-y-auto p-4">
                {messages.map((message) => (
                  <MessageBubble
                    key={message.message_id}
                    message={message}
                    overlaySources={messageSources[message.message_id]}
                  />
                ))}
                {sendMutation.isPending ? (
                  <div className="flex justify-start">
                    <div className="rounded-2xl bg-muted px-4 py-2 text-sm text-muted-foreground">
                      Assistant is typing…
                    </div>
                  </div>
                ) : null}
                <div ref={messagesEndRef} />
              </div>

              {canStartChat ? (
                <form
                  className="flex gap-2 border-t border-border p-4"
                  onSubmit={messageForm.handleSubmit((values) => sendMutation.mutate(values))}
                >
                  <Input
                    placeholder="Type your message…"
                    disabled={sendMutation.isPending}
                    {...messageForm.register("content")}
                  />
                  <Button type="submit" disabled={sendMutation.isPending}>
                    Send
                  </Button>
                </form>
              ) : null}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  overlaySources,
}: {
  message: ChatMessage;
  overlaySources?: ChatSource[];
}) {
  const assistant = isAssistant(message.sender_type);
  const sources = overlaySources ?? asSources(message.citations);

  return (
    <div className={cn("flex", assistant ? "justify-start" : "justify-end")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2 text-sm",
          assistant ? "bg-muted text-foreground" : "bg-teal-700 text-white",
        )}
      >
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide opacity-70">
          {message.sender_type}
        </div>
        {assistant ? (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}
        <div className="mt-1 text-[10px] opacity-60">{formatDate(message.created_at)}</div>

        {assistant && sources.length > 0 ? (
          <div className="mt-3 space-y-2 border-t border-border/40 pt-2">
            <div className="text-[10px] font-semibold uppercase tracking-wide opacity-70">
              Sources
            </div>
            {sources.map((source) => (
              <div
                key={`${source.chunk_id ?? source.chunk_uuid ?? "x"}-${source.document_id}`}
                className="rounded-md bg-background/60 p-2 text-xs text-foreground"
              >
                <div className="flex flex-wrap items-center gap-1">
                  <span className="font-medium">{source.document_name}</span>
                  {source.page !== null && source.page !== undefined ? (
                    <Badge variant="outline">p.{source.page}</Badge>
                  ) : null}
                  <Badge variant="secondary">{(source.score * 100).toFixed(0)}%</Badge>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
