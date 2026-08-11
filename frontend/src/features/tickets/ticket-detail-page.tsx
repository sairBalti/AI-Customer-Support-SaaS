import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  assignTicket,
  closeTicket,
  getTicket,
  resolveTicket,
  updateTicket,
} from "@/api/tickets";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";
import { cn, formatDate } from "@/lib/utils";

const WORKFLOW = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"] as const;

function statusVariant(status: string): "success" | "warning" | "danger" | "secondary" | "outline" {
  switch (status) {
    case "OPEN":
      return "outline";
    case "IN_PROGRESS":
      return "warning";
    case "RESOLVED":
      return "success";
    case "CLOSED":
      return "secondary";
    default:
      return "secondary";
  }
}

function priorityVariant(priority: string): "success" | "warning" | "danger" | "secondary" | "outline" {
  switch (priority) {
    case "LOW":
      return "secondary";
    case "MEDIUM":
      return "outline";
    case "HIGH":
      return "warning";
    case "URGENT":
      return "danger";
    default:
      return "secondary";
  }
}

export function TicketDetailPage() {
  const { ticketId } = useParams();
  const id = Number(ticketId);
  const { can } = useAuth();
  const qc = useQueryClient();
  const [assignUserId, setAssignUserId] = useState("");
  const [priority, setPriority] = useState("");

  const query = useQuery({
    queryKey: ["tickets", id],
    queryFn: () => getTicket(id),
    enabled: Number.isFinite(id),
  });

  useEffect(() => {
    if (query.data?.priority && !priority) {
      setPriority(query.data.priority);
    }
  }, [query.data, priority]);

  const invalidate = () => void qc.invalidateQueries({ queryKey: ["tickets", id] });

  const updateMutation = useMutation({
    mutationFn: (payload: { priority: string }) => updateTicket(id, payload),
    onSuccess: () => {
      toast.success("Ticket updated");
      invalidate();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const assignMutation = useMutation({
    mutationFn: (assignedTo: number) => assignTicket(id, assignedTo),
    onSuccess: () => {
      toast.success("Ticket assigned");
      setAssignUserId("");
      invalidate();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const resolveMutation = useMutation({
    mutationFn: () => resolveTicket(id),
    onSuccess: () => {
      toast.success("Ticket resolved");
      invalidate();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const closeMutation = useMutation({
    mutationFn: () => closeTicket(id),
    onSuccess: () => {
      toast.success("Ticket closed");
      invalidate();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  if (query.isLoading) return <LoadingBlock />;
  if (query.error) return <ErrorBlock message={getErrorMessage(query.error)} />;
  if (!query.data) return null;

  const ticket = query.data;
  const currentStep = WORKFLOW.indexOf(ticket.status as (typeof WORKFLOW)[number]);

  return (
    <div>
      <PageHeader
        title={ticket.subject}
        description={`Ticket ${ticket.ticket_number}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Badge variant={statusVariant(ticket.status)}>{ticket.status}</Badge>
            <Badge variant={priorityVariant(ticket.priority)}>{ticket.priority}</Badge>
          </div>
        }
      />

      <div className="mb-6 flex flex-wrap items-center gap-2">
        {WORKFLOW.map((step, index) => {
          const active = ticket.status === step;
          const completed = currentStep > index;
          return (
            <div key={step} className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-8 min-w-8 items-center justify-center rounded-full border px-2 text-xs font-semibold",
                  active && "border-teal-600 bg-teal-600 text-white",
                  completed && !active && "border-teal-200 bg-teal-50 text-teal-800",
                  !active && !completed && "border-border bg-muted text-muted-foreground",
                )}
              >
                {index + 1}
              </div>
              <span
                className={cn(
                  "text-xs font-medium",
                  active ? "text-teal-800" : "text-muted-foreground",
                )}
              >
                {step.replace("_", " ")}
              </span>
              {index < WORKFLOW.length - 1 ? (
                <div
                  className={cn(
                    "hidden h-px w-6 sm:block",
                    completed ? "bg-teal-400" : "bg-border",
                  )}
                />
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <DetailRow label="Description" value={ticket.description} />
            <DetailRow label="Category" value={ticket.category} />
            <DetailRow label="Source" value={ticket.source} />
            <DetailRow
              label="Conversation"
              value={
                ticket.conversation_id ? (
                  <Link
                    className="text-teal-800 hover:underline"
                    to={`/app/chat?conversation=${ticket.conversation_id}`}
                  >
                    #{ticket.conversation_id}
                  </Link>
                ) : (
                  "—"
                )
              }
            />
            <DetailRow label="Assigned to" value={ticket.assigned_to ? `#${ticket.assigned_to}` : "—"} />
            <DetailRow label="Created" value={formatDate(ticket.created_at)} />
            <DetailRow label="Updated" value={formatDate(ticket.updated_at)} />
            <DetailRow label="Resolved" value={formatDate(ticket.resolved_at)} />
            <DetailRow label="Closed" value={formatDate(ticket.closed_at)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {can("tickets.update") && ticket.status !== "CLOSED" ? (
              <div className="space-y-2">
                <Label>Update priority</Label>
                <div className="flex gap-2">
                  <select
                    className="flex h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm"
                    value={priority || ticket.priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="URGENT">URGENT</option>
                  </select>
                  <Button
                    variant="outline"
                    disabled={updateMutation.isPending}
                    onClick={() =>
                      updateMutation.mutate({ priority: priority || ticket.priority })
                    }
                  >
                    Save
                  </Button>
                </div>
              </div>
            ) : null}

            {can("tickets.assign") && ticket.status !== "CLOSED" ? (
              <div className="space-y-2">
                <Label>Assign to user ID</Label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    placeholder="User ID"
                    value={assignUserId}
                    onChange={(e) => setAssignUserId(e.target.value)}
                  />
                  <Button
                    variant="outline"
                    disabled={assignMutation.isPending || !assignUserId}
                    onClick={() => assignMutation.mutate(Number(assignUserId))}
                  >
                    Assign
                  </Button>
                </div>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              {can("tickets.resolve") && ticket.status !== "RESOLVED" && ticket.status !== "CLOSED" ? (
                <Button
                  variant="secondary"
                  disabled={resolveMutation.isPending}
                  onClick={() => resolveMutation.mutate()}
                >
                  Resolve
                </Button>
              ) : null}
              {can("tickets.close") && ticket.status !== "CLOSED" ? (
                <Button
                  variant="destructive"
                  disabled={closeMutation.isPending}
                  onClick={() => {
                    if (!window.confirm("Close this ticket? This cannot be undone easily.")) return;
                    closeMutation.mutate();
                  }}
                >
                  Close
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="flex justify-between gap-4 border-b border-border py-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="max-w-[60%] text-right font-medium">{value}</span>
    </div>
  );
}
