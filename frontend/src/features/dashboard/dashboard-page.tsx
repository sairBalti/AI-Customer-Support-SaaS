import { useMemo, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useQueries, useQuery } from "@tanstack/react-query";
import {
  ArrowDownRight,
  ArrowRight,
  Braces,
  CalendarDays,
  FileText,
  MessageSquare,
  Ticket as TicketIcon,
} from "lucide-react";
import { toast } from "sonner";
import { getConversation, listConversations } from "@/api/chat";
import { listDocuments } from "@/api/documents";
import { listTickets } from "@/api/tickets";
import { listUsers } from "@/api/users";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorBlock } from "@/components/ui/page";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";
import { cn } from "@/lib/utils";
import type { Ticket } from "@/types/api";

const PRIORITY_RANK: Record<string, number> = {
  URGENT: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

export function DashboardPage() {
  const { can } = useAuth();
  const canTickets = can("tickets.read");
  const canDocs = can("documents.read");
  const canChat = can("chat.read") || can("chat.start");
  const canUsers = can("users.read");

  const openTickets = useQuery({
    queryKey: ["dashboard", "tickets-open"],
    queryFn: () => listTickets({ page: 1, page_size: 1, status: "OPEN" }),
    enabled: canTickets,
  });
  const ticketsSample = useQuery({
    queryKey: ["dashboard", "tickets-sample"],
    queryFn: () =>
      listTickets({ page: 1, page_size: 100, sort_by: "created_at", sort_order: "desc" }),
    enabled: canTickets,
  });
  const documents = useQuery({
    queryKey: ["dashboard", "documents"],
    queryFn: () =>
      listDocuments({ page: 1, page_size: 100, sort_by: "created_at", sort_order: "desc" }),
    enabled: canDocs,
  });
  const conversations = useQuery({
    queryKey: ["dashboard", "chat"],
    queryFn: () => listConversations({ limit: 50, offset: 0 }),
    enabled: canChat,
  });
  const users = useQuery({
    queryKey: ["dashboard", "users"],
    queryFn: () => listUsers({ page: 1, page_size: 100 }),
    enabled: canUsers,
  });

  const liveSessions = useMemo(() => {
    const items = conversations.data?.items ?? [];
    return [...items]
      .filter((c) => ["ACTIVE", "WAITING_CUSTOMER", "WAITING_AI"].includes(c.status))
      .sort(
        (a, b) =>
          new Date(b.last_message_at || b.updated_at).getTime() -
          new Date(a.last_message_at || a.updated_at).getTime(),
      )
      .slice(0, 3);
  }, [conversations.data]);

  const liveMessages = useQueries({
    queries: liveSessions.map((session) => ({
      queryKey: ["dashboard", "chat-preview", session.conversation_id],
      queryFn: () => getConversation(session.conversation_id),
      enabled: canChat && liveSessions.length > 0,
      staleTime: 30_000,
    })),
  });

  const loading =
    (canTickets && (openTickets.isLoading || ticketsSample.isLoading)) ||
    (canDocs && documents.isLoading) ||
    (canChat && conversations.isLoading);
  const livePreviewLoading =
    canChat &&
    !conversations.isLoading &&
    liveSessions.length > 0 &&
    liveMessages.some((q) => q.isLoading);
  const error =
    openTickets.error || ticketsSample.error || documents.error || conversations.error;

  const docTotal = documents.data?.meta.total_items ?? 0;
  const chunkTotal = (documents.data?.items ?? []).reduce(
    (sum, doc) => sum + (doc.total_chunks || 0),
    0,
  );
  const conversationCount = conversations.data?.items.length ?? 0;
  const openCount = openTickets.data?.meta.total_items ?? 0;

  const chartDays = useMemo(
    () => buildSupportSeries(ticketsSample.data?.items ?? []),
    [ticketsSample.data],
  );
  const maxBar = Math.max(1, ...chartDays.map((d) => d.resolved + d.escalated));

  const priorityTickets = useMemo(() => {
    const items = ticketsSample.data?.items ?? [];
    return [...items]
      .filter((t) => t.status === "OPEN" || t.status === "IN_PROGRESS")
      .sort((a, b) => {
        const pa = PRIORITY_RANK[a.priority] ?? 9;
        const pb = PRIORITY_RANK[b.priority] ?? 9;
        if (pa !== pb) return pa - pb;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      })
      .slice(0, 5);
  }, [ticketsSample.data]);

  const userName = (userId: number) => {
    const u = users.data?.items.find((item) => item.user_id === userId);
    if (!u) return `Customer #${userId}`;
    return u.display_name || `${u.first_name} ${u.last_name}`.trim();
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
            Dashboard Overview
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Real-time metrics and system health for AI operations.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" className="bg-white" type="button">
            <CalendarDays className="h-4 w-4 text-slate-500" />
            Today
          </Button>
          <Button
            type="button"
            onClick={() =>
              toast.message("Report export is not available yet from this dashboard.")
            }
          >
            Generate Report
          </Button>
        </div>
      </header>

      {error ? <ErrorBlock message={getErrorMessage(error)} /> : null}

      {loading ? (
        <DashboardSkeleton
          metricCount={(canDocs ? 2 : 0) + (canChat ? 1 : 0) + (canTickets ? 1 : 0)}
          showChart={canTickets}
          showLiveConversations={canChat}
          showTicketsTable={canTickets}
        />
      ) : (
        <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {canDocs ? (
          <MetricCard
            label="Total Documents"
            value={formatCompact(docTotal)}
            hint={docTotal === 0 ? "No documents yet" : "In your document library"}
            icon={<FileText className="h-4 w-4" />}
          />
        ) : null}
        {canDocs ? (
          <MetricCard
            label="Knowledge Chunks"
            value={formatCompact(chunkTotal)}
            hint={
              (documents.data?.meta.total_items ?? 0) > (documents.data?.items.length ?? 0)
                ? `From latest ${documents.data?.items.length ?? 0} documents`
                : "Indexed across documents"
            }
            icon={<Braces className="h-4 w-4" />}
          />
        ) : null}
        {canChat ? (
          <MetricCard
            label="AI Conversations"
            value={formatCompact(conversationCount)}
            hint="Recent conversations (API page)"
            icon={<MessageSquare className="h-4 w-4" />}
          />
        ) : null}
        {canTickets ? (
          <MetricCard
            label="Open Tickets"
            value={formatCompact(openCount)}
            hint={openCount > 0 ? "Needs attention" : "Queue is clear"}
            hintTone={openCount > 0 ? "danger" : "muted"}
            icon={<TicketIcon className="h-4 w-4" />}
            iconTone="rose"
            trendDown={openCount > 0}
          />
        ) : null}
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,1fr)]">
        <Card className="overflow-hidden shadow-none">
          <CardContent className="p-6">
            <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">AI Support Overview</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Resolution rate vs escalation over 7 days.
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span className="inline-flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-teal-800" /> Resolved
                </span>
                <span className="inline-flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-slate-400" /> Escalated
                </span>
              </div>
            </div>
            {canTickets ? (
              <div className="rounded-lg bg-[linear-gradient(to_top,#eef2f6_1px,transparent_1px)] bg-[length:100%_32px] px-2 pt-2">
                <div className="flex h-52 items-end gap-3 pb-1">
                  {chartDays.map((day) => {
                    const resolvedPct = (day.resolved / maxBar) * 100;
                    const escalatedPct = (day.escalated / maxBar) * 100;
                    return (
                      <div key={day.key} className="flex flex-1 flex-col items-center gap-2">
                        <div className="flex h-40 w-full max-w-12 flex-col justify-end gap-0.5">
                          <div
                            className="w-full rounded-t-md bg-teal-800 transition-all duration-500"
                            style={{
                              height: `${day.resolved ? Math.max(10, resolvedPct) : 0}%`,
                            }}
                            title={`Resolved: ${day.resolved}`}
                          />
                          <div
                            className="w-full rounded-b-md bg-slate-400 transition-all duration-500"
                            style={{
                              height: `${day.escalated ? Math.max(8, escalatedPct) : 0}%`,
                            }}
                            title={`Escalated: ${day.escalated}`}
                          />
                        </div>
                        <span className="text-xs font-medium text-slate-500">{day.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Ticket analytics require tickets.read.</p>
            )}
            {canTickets && chartDays.every((d) => d.resolved + d.escalated === 0) ? (
              <p className="mt-3 text-xs text-slate-400">
                No resolved or escalated ticket activity in the last 7 days (from latest ticket
                page).
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card className="shadow-none">
          <CardContent className="p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900">Live Conversations</h2>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                {liveSessions.length} Active
              </span>
            </div>
            {!canChat ? (
              <p className="text-sm text-slate-500">Chat access is required to view live sessions.</p>
            ) : livePreviewLoading ? (
              <LiveConversationsSkeleton rows={liveSessions.length} />
            ) : liveSessions.length === 0 ? (
              <p className="text-sm text-slate-500">No active conversations right now.</p>
            ) : (
              <ul className="space-y-4">
                {liveSessions.map((session, index) => {
                  const preview = liveMessages[index]?.data;
                  const lastUserMsg = [...(preview?.messages ?? [])]
                    .reverse()
                    .find((m) => m.sender_type === "CUSTOMER");
                  const snippet =
                    lastUserMsg?.content || session.title || "Conversation in progress";
                  const name = canUsers
                    ? userName(session.customer_id)
                    : session.title || `Customer #${session.customer_id}`;
                  return (
                    <li key={session.conversation_id}>
                      <Link
                        to={`/app/chat?conversation=${session.conversation_id}`}
                        className="flex gap-3 rounded-lg p-1 transition hover:bg-slate-50"
                      >
                        <Avatar name={name} online />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-baseline justify-between gap-2">
                            <span className="truncate text-sm font-semibold text-slate-900">
                              {name}
                            </span>
                            <span className="shrink-0 text-xs text-slate-400">
                              {relativeTime(session.last_message_at || session.updated_at)}
                            </span>
                          </div>
                          <p className="mt-0.5 truncate text-sm text-slate-500">
                            “{truncate(snippet, 42)}”
                          </p>
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </section>

      {canTickets ? (
        <Card className="shadow-none">
          <CardContent className="p-0">
            <div className="flex items-center justify-between gap-3 px-6 py-5">
              <h2 className="text-lg font-semibold text-slate-900">
                Priority Tickets (Human Escalation)
              </h2>
              <Link
                to="/app/tickets"
                className="inline-flex items-center gap-1 text-sm font-semibold text-teal-800 hover:text-teal-900"
              >
                View All <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>ID</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {priorityTickets.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-8 text-center text-slate-500">
                      No open priority tickets.
                    </TableCell>
                  </TableRow>
                ) : (
                  priorityTickets.map((ticket) => (
                    <TableRow key={ticket.ticket_id}>
                      <TableCell className="font-medium text-slate-700">
                        {formatTicketId(ticket)}
                      </TableCell>
                      <TableCell className="max-w-[280px] truncate font-medium text-slate-900">
                        {ticket.subject}
                      </TableCell>
                      <TableCell className="text-slate-600">
                        {canUsers ? userName(ticket.customer_id) : `#${ticket.customer_id}`}
                      </TableCell>
                      <TableCell>
                        <PriorityPill priority={ticket.priority} />
                      </TableCell>
                      <TableCell className="text-right">
                        <Link
                          to={`/app/tickets/${ticket.ticket_id}`}
                          className="font-semibold text-teal-800 hover:text-teal-900"
                        >
                          Review
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
        </>
      )}
    </div>
  );
}

function DashboardSkeleton({
  metricCount,
  showChart,
  showLiveConversations,
  showTicketsTable,
}: {
  metricCount: number;
  showChart: boolean;
  showLiveConversations: boolean;
  showTicketsTable: boolean;
}) {
  return (
    <>
      {metricCount > 0 ? (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: metricCount }).map((_, index) => (
            <MetricCardSkeleton key={index} />
          ))}
        </section>
      ) : null}

      {showChart || showLiveConversations ? (
        <section className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,1fr)]">
          {showChart ? <ChartSkeleton /> : null}
          {showLiveConversations ? <LiveConversationsPanelSkeleton /> : null}
        </section>
      ) : null}

      {showTicketsTable ? <TicketsTableSkeleton /> : null}
    </>
  );
}

function MetricCardSkeleton() {
  return (
    <Card className="shadow-none">
      <CardContent className="relative p-5">
        <Skeleton className="absolute right-5 top-5 h-10 w-10 rounded-xl" />
        <Skeleton className="h-3 w-28" />
        <Skeleton className="mt-4 h-9 w-24" />
        <Skeleton className="mt-3 h-4 w-32" />
      </CardContent>
    </Card>
  );
}

function ChartSkeleton() {
  return (
    <Card className="overflow-hidden shadow-none">
      <CardContent className="p-6">
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2">
            <Skeleton className="h-5 w-44" />
            <Skeleton className="h-4 w-56" />
          </div>
          <div className="flex gap-4">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
          </div>
        </div>
        <div className="rounded-lg bg-slate-50 px-2 pt-2">
          <div className="flex h-52 items-end gap-3 pb-6">
            {Array.from({ length: 7 }).map((_, index) => (
              <div key={index} className="flex flex-1 flex-col items-center gap-2">
                <Skeleton
                  className="w-full max-w-12 rounded-md"
                  style={{ height: `${35 + (index % 4) * 12}%` }}
                />
                <Skeleton className="h-3 w-8" />
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function LiveConversationsPanelSkeleton() {
  return (
    <Card className="shadow-none">
      <CardContent className="p-6">
        <div className="mb-5 flex items-center justify-between gap-3">
          <Skeleton className="h-5 w-36" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
        <LiveConversationsSkeleton rows={3} />
      </CardContent>
    </Card>
  );
}

function LiveConversationsSkeleton({ rows }: { rows: number }) {
  return (
    <ul className="space-y-4">
      {Array.from({ length: rows }).map((_, index) => (
        <li key={index} className="flex gap-3">
          <Skeleton className="h-10 w-10 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-4 w-full max-w-[220px]" />
          </div>
        </li>
      ))}
    </ul>
  );
}

function TicketsTableSkeleton() {
  return (
    <Card className="shadow-none">
      <CardContent className="p-0">
        <div className="flex items-center justify-between gap-3 px-6 py-5">
          <Skeleton className="h-5 w-64" />
          <Skeleton className="h-4 w-20" />
        </div>
        <div className="border-t border-border px-3 py-2">
          <div className="flex gap-4 border-b border-border px-3 py-3">
            {["w-16", "w-32", "w-24", "w-16", "w-14"].map((width, index) => (
              <Skeleton key={index} className={cn("h-3", width)} />
            ))}
          </div>
          {Array.from({ length: 3 }).map((_, row) => (
            <div
              key={row}
              className="flex items-center gap-4 border-b border-border px-3 py-4 last:border-0"
            >
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 flex-1 max-w-xs" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="ml-auto h-4 w-14" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function MetricCard({
  label,
  value,
  hint,
  icon,
  iconTone = "muted",
  hintTone = "muted",
  trendDown = false,
}: {
  label: string;
  value: string;
  hint: string;
  icon: ReactNode;
  iconTone?: "muted" | "rose";
  hintTone?: "muted" | "danger";
  trendDown?: boolean;
}) {
  return (
    <Card className="shadow-none">
      <CardContent className="relative p-5">
        <div
          className={cn(
            "absolute right-5 top-5 flex h-10 w-10 items-center justify-center rounded-xl",
            iconTone === "rose" ? "bg-rose-50 text-rose-500" : "bg-slate-100 text-slate-500",
          )}
        >
          {icon}
        </div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
          {label}
        </p>
        <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</p>
        <p
          className={cn(
            "mt-2 inline-flex items-center gap-1 text-sm",
            hintTone === "danger" ? "text-rose-500" : "text-slate-500",
          )}
        >
          {trendDown ? <ArrowDownRight className="h-3.5 w-3.5" /> : null}
          {hint}
        </p>
      </CardContent>
    </Card>
  );
}

function Avatar({ name, online }: { name: string; online?: boolean }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
  return (
    <div className="relative shrink-0">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-700">
        {initials || "?"}
      </div>
      {online ? (
        <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-white bg-emerald-500" />
      ) : null}
    </div>
  );
}

function PriorityPill({ priority }: { priority: string }) {
  const label = priority.charAt(0) + priority.slice(1).toLowerCase();
  const high = priority === "HIGH" || priority === "URGENT";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        high ? "bg-rose-50 text-rose-600" : "bg-indigo-50 text-indigo-600",
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", high ? "bg-rose-500" : "bg-indigo-500")} />
      {label}
    </span>
  );
}

function buildSupportSeries(tickets: Ticket[]) {
  const days = Array.from({ length: 7 }, (_, index) => {
    const day = new Date();
    day.setHours(0, 0, 0, 0);
    day.setDate(day.getDate() - (6 - index));
    return day;
  });

  return days.map((day) => {
    const next = new Date(day);
    next.setDate(next.getDate() + 1);
    const inDay = (iso?: string | null) => {
      if (!iso) return false;
      const t = new Date(iso).getTime();
      return t >= day.getTime() && t < next.getTime();
    };
    const resolved = tickets.filter(
      (t) =>
        (t.status === "RESOLVED" || t.status === "CLOSED") &&
        inDay(t.resolved_at || t.closed_at || t.updated_at),
    ).length;
    const escalated = tickets.filter(
      (t) => (t.source === "AI_CHAT" || t.conversation_id != null) && inDay(t.created_at),
    ).length;
    return {
      key: day.toISOString(),
      label: day.toLocaleDateString(undefined, { weekday: "short" }),
      resolved,
      escalated,
    };
  });
}

function formatCompact(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 10_000) return `${(value / 1_000).toFixed(1)}k`;
  return value.toLocaleString();
}

function truncate(value: string, max: number) {
  const clean = value.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1)}…`;
}

function relativeTime(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.max(0, Math.floor(diffMs / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatTicketId(ticket: Ticket) {
  if (ticket.ticket_number) return `#${ticket.ticket_number.replace(/^#/, "")}`;
  return `#T-${ticket.ticket_id}`;
}
