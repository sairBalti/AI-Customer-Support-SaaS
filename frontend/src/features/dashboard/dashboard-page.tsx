import { useQuery } from "@tanstack/react-query";
import { listConversations } from "@/api/chat";
import { listDocuments, getStorageUsage } from "@/api/documents";
import { listTickets } from "@/api/tickets";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";

export function DashboardPage() {
  const { user, can } = useAuth();

  const tickets = useQuery({
    queryKey: ["dashboard", "tickets"],
    queryFn: () => listTickets({ page: 1, page_size: 1 }),
    enabled: can("tickets.read"),
  });
  const documents = useQuery({
    queryKey: ["dashboard", "documents"],
    queryFn: () => listDocuments({ page: 1, page_size: 1 }),
    enabled: can("documents.read"),
  });
  const storage = useQuery({
    queryKey: ["dashboard", "storage"],
    queryFn: () => getStorageUsage(),
    enabled: can("documents.read"),
  });
  const conversations = useQuery({
    queryKey: ["dashboard", "chat"],
    queryFn: () => listConversations({ limit: 50, offset: 0 }),
    enabled: can("chat.read") || can("chat.start"),
  });

  const loading =
    tickets.isLoading || documents.isLoading || storage.isLoading || conversations.isLoading;
  const error =
    tickets.error || documents.error || storage.error || conversations.error;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description={`Welcome back, ${user?.first_name ?? "there"}. Metrics use live list totals from available APIs.`}
      />
      {loading ? <LoadingBlock /> : null}
      {error ? <ErrorBlock message={getErrorMessage(error)} /> : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {can("tickets.read") ? (
          <Metric title="Tickets" value={tickets.data?.meta.total_items ?? 0} />
        ) : null}
        {can("documents.read") ? (
          <Metric title="Documents" value={documents.data?.meta.total_items ?? 0} />
        ) : null}
        {can("documents.read") ? (
          <Metric
            title="Storage used"
            value={
              storage.data
                ? Number((storage.data.used_bytes / (1024 * 1024)).toFixed(1))
                : 0
            }
            hint={
              storage.data
                ? `MB of ${(storage.data.max_storage_bytes / (1024 * 1024)).toFixed(0)} MB`
                : undefined
            }
          />
        ) : null}
        {can("chat.read") || can("chat.start") ? (
          <Metric title="Conversations" value={conversations.data?.items.length ?? 0} hint="latest page" />
        ) : null}
      </div>
    </div>
  );
}

function Metric({ title, value, hint }: { title: string; value: number; hint?: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-semibold">{value}</div>
        {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}
