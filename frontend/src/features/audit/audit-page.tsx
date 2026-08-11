import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAuditLog, listAuditLogs } from "@/api/audit";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getErrorMessage } from "@/lib/api-error";
import { formatDate } from "@/lib/utils";
import type { AuditLog } from "@/types/api";

export function AuditPage() {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");
  const [actorUserIdFilter, setActorUserIdFilter] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const actorUserId = actorUserIdFilter.trim() ? Number(actorUserIdFilter) : undefined;
  const actorFilterValid =
    actorUserId === undefined || (Number.isFinite(actorUserId) && actorUserId > 0);

  const listQuery = useQuery({
    queryKey: ["audit-logs", page, actionFilter, entityTypeFilter, actorUserIdFilter],
    queryFn: () =>
      listAuditLogs({
        page,
        page_size: 20,
        ...(actionFilter ? { action: actionFilter } : {}),
        ...(entityTypeFilter ? { entity_type: entityTypeFilter } : {}),
        ...(actorFilterValid && actorUserId !== undefined
          ? { actor_user_id: actorUserId }
          : {}),
      }),
  });

  const detailQuery = useQuery({
    queryKey: ["audit-logs", "detail", selectedId],
    queryFn: () => getAuditLog(selectedId!),
    enabled: selectedId !== null,
  });

  const meta = listQuery.data?.meta;

  return (
    <div>
      <PageHeader
        title="Audit log"
        description="Read-only activity trail for compliance and troubleshooting."
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-1">
          <Label htmlFor="action-filter">Action</Label>
          <Input
            id="action-filter"
            placeholder="e.g. users.create"
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="entity-filter">Entity type</Label>
          <Input
            id="entity-filter"
            placeholder="e.g. users"
            value={entityTypeFilter}
            onChange={(e) => {
              setEntityTypeFilter(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="actor-filter">Actor user ID</Label>
          <Input
            id="actor-filter"
            type="number"
            min={1}
            placeholder="Optional"
            value={actorUserIdFilter}
            onChange={(e) => {
              setActorUserIdFilter(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="space-y-1">
          <Label>Page</Label>
          <div className="flex items-center gap-2 pt-1">
            <Button
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Prev
            </Button>
            <span className="text-sm text-muted-foreground">
              {meta ? `${meta.page} / ${meta.total_pages}` : page}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={!meta || page >= meta.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </div>

      {listQuery.isLoading ? <LoadingBlock /> : null}
      {listQuery.error ? <ErrorBlock message={getErrorMessage(listQuery.error)} /> : null}

      {listQuery.data && listQuery.data.items.length === 0 ? (
        <EmptyState title="No audit entries" description="Try adjusting filters or check back later." />
      ) : null}

      {listQuery.data && listQuery.data.items.length > 0 ? (
        <div className="rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Created</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Entity</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>UUID</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {listQuery.data.items.map((log) => (
                <TableRow
                  key={log.audit_log_id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => setSelectedId(log.audit_log_id)}
                >
                  <TableCell>{formatDate(log.created_at)}</TableCell>
                  <TableCell className="font-medium">{log.action}</TableCell>
                  <TableCell>
                    {log.entity_type}
                    {log.entity_id !== null ? ` #${log.entity_id}` : ""}
                  </TableCell>
                  <TableCell>
                    {log.actor_user_id !== null ? `#${log.actor_user_id}` : "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {log.audit_uuid ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      <Dialog open={selectedId !== null} onOpenChange={(open) => !open && setSelectedId(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Audit entry detail</DialogTitle>
          </DialogHeader>
          {detailQuery.isLoading ? <LoadingBlock label="Loading detail…" /> : null}
          {detailQuery.error ? <ErrorBlock message={getErrorMessage(detailQuery.error)} /> : null}
          {detailQuery.data ? <AuditDetail log={detailQuery.data} /> : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function AuditDetail({ log }: { log: AuditLog }) {
  return (
    <div className="space-y-4 text-sm">
      <div className="grid gap-2 sm:grid-cols-2">
        <Field label="Action" value={log.action} />
        <Field label="Entity" value={`${log.entity_type}${log.entity_id !== null ? ` #${log.entity_id}` : ""}`} />
        <Field label="Actor" value={log.actor_user_id !== null ? `#${log.actor_user_id}` : "—"} />
        <Field label="Created" value={formatDate(log.created_at)} />
        <Field label="IP address" value={log.ip_address ?? "—"} />
        <Field label="UUID" value={log.audit_uuid ?? "—"} mono />
      </div>

      {log.description ? (
        <div>
          <div className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
            Description
          </div>
          <p>{log.description}</p>
        </div>
      ) : null}

      <div>
        <div className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
          User agent
        </div>
        <p className="break-all text-muted-foreground">{log.user_agent ?? "—"}</p>
      </div>

      <div>
        <div className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
          Metadata
        </div>
        <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs">
          {JSON.stringify(log.metadata, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={mono ? "font-mono text-xs" : "font-medium"}>{value}</div>
    </div>
  );
}
