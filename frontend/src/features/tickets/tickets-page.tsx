import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { createTicket, listTickets } from "@/api/tickets";
import { listUsers } from "@/api/users";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";
import { formatDate } from "@/lib/utils";

const createSchema = z.object({
  subject: z.string().min(1),
  description: z.string().min(1),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "URGENT"]),
  category: z.enum(["GENERAL", "TECHNICAL", "BILLING", "ACCOUNT", "OTHER"]),
  customer_id: z.number().int().positive().optional(),
});

type CreateValues = z.infer<typeof createSchema>;

const STATUS_OPTIONS = ["", "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"] as const;

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

export function TicketsPage() {
  const { can, user } = useAuth();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const isCustomer = (user?.role_name || "").toUpperCase() === "CUSTOMER";
  const needsCustomerId = !isCustomer;

  const query = useQuery({
    queryKey: ["tickets", statusFilter],
    queryFn: () =>
      listTickets({
        page: 1,
        page_size: 50,
        ...(statusFilter ? { status: statusFilter } : {}),
      }),
  });

  const usersQuery = useQuery({
    queryKey: ["users", "ticket-create"],
    queryFn: () => listUsers({ page: 1, page_size: 100 }),
    enabled: open && needsCustomerId && can("users.read"),
  });

  const customerOptions = useMemo(() => {
    const items = usersQuery.data?.items ?? [];
    const customers = items.filter((u) => (u.role_name || "").toUpperCase() === "CUSTOMER");
    return customers.length > 0 ? customers : items;
  }, [usersQuery.data?.items]);

  const defaultCustomerId = useMemo(() => {
    const items = usersQuery.data?.items ?? [];
    const customers = items.filter((u) => (u.role_name || "").toUpperCase() === "CUSTOMER");
    return customers[0]?.user_id ?? user?.user_id;
  }, [usersQuery.data?.items, user?.user_id]);

  const form = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      subject: "",
      description: "",
      priority: "MEDIUM",
      category: "GENERAL",
      customer_id: user?.user_id,
    },
  });

  useEffect(() => {
    if (open && defaultCustomerId) {
      form.setValue("customer_id", defaultCustomerId);
    }
  }, [open, defaultCustomerId, form]);

  const createMutation = useMutation({
    mutationFn: (values: CreateValues) => {
      const payload: Record<string, unknown> = {
        subject: values.subject,
        description: values.description,
        priority: values.priority,
        category: values.category,
      };
      if (needsCustomerId) {
        if (!values.customer_id) {
          throw new Error("Customer is required when creating tickets as staff.");
        }
        payload.customer_id = values.customer_id;
      }
      return createTicket(payload);
    },
    onSuccess: () => {
      toast.success("Ticket created");
      setOpen(false);
      form.reset({
        subject: "",
        description: "",
        priority: "MEDIUM",
        category: "GENERAL",
        customer_id: defaultCustomerId ?? user?.user_id,
      });
      void qc.invalidateQueries({ queryKey: ["tickets"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title="Tickets"
        description="Support tickets and escalations."
        actions={
          can("tickets.create") ? (
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button>Create ticket</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create ticket</DialogTitle>
                  <DialogDescription>
                    {needsCustomerId
                      ? "Staff must choose the customer this ticket belongs to."
                      : "Submit a new support request."}
                  </DialogDescription>
                </DialogHeader>
                <form
                  className="space-y-3"
                  onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
                >
                  {needsCustomerId ? (
                    <div className="space-y-1">
                      <Label>Customer</Label>
                      {can("users.read") && customerOptions.length ? (
                        <select
                          className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                          {...form.register("customer_id", { valueAsNumber: true })}
                        >
                          {customerOptions.map((u) => (
                            <option key={u.user_id} value={u.user_id}>
                              {u.display_name || `${u.first_name} ${u.last_name}`} ({u.email})
                            </option>
                          ))}
                        </select>
                      ) : (
                        <Input
                          type="number"
                          min={1}
                          placeholder="Customer user ID"
                          {...form.register("customer_id", { valueAsNumber: true })}
                        />
                      )}
                      <p className="text-xs text-muted-foreground">
                        Prefers CUSTOMER role users when available.
                      </p>
                    </div>
                  ) : null}
                  <div className="space-y-1">
                    <Label htmlFor="ticket-subject">Subject</Label>
                    <Input id="ticket-subject" {...form.register("subject")} />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="ticket-description">Description</Label>
                    <Textarea id="ticket-description" rows={4} {...form.register("description")} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label>Priority</Label>
                      <select
                        className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                        {...form.register("priority")}
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
                        {...form.register("category")}
                      >
                        <option value="GENERAL">GENERAL</option>
                        <option value="TECHNICAL">TECHNICAL</option>
                        <option value="BILLING">BILLING</option>
                        <option value="ACCOUNT">ACCOUNT</option>
                        <option value="OTHER">OTHER</option>
                      </select>
                    </div>
                  </div>
                  <Button type="submit" disabled={createMutation.isPending}>
                    Create
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          ) : null
        }
      />

      <div className="mb-4 flex items-center gap-3">
        <Label htmlFor="status-filter">Status</Label>
        <select
          id="status-filter"
          className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          {STATUS_OPTIONS.map((status) => (
            <option key={status || "all"} value={status}>
              {status || "All statuses"}
            </option>
          ))}
        </select>
      </div>

      {query.isLoading ? <LoadingBlock /> : null}
      {query.error ? <ErrorBlock message={getErrorMessage(query.error)} /> : null}

      {query.data && query.data.items.length === 0 ? (
        <EmptyState title="No tickets" description="Create a ticket or adjust the status filter." />
      ) : null}

      {query.data && query.data.items.length > 0 ? (
        <div className="rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Number</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data.items.map((ticket) => (
                <TableRow key={ticket.ticket_id}>
                  <TableCell className="font-mono text-xs">{ticket.ticket_number}</TableCell>
                  <TableCell>
                    <Link
                      className="font-medium text-teal-800 hover:underline"
                      to={`/app/tickets/${ticket.ticket_id}`}
                    >
                      {ticket.subject}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariant(ticket.status)}>{ticket.status}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={priorityVariant(ticket.priority)}>{ticket.priority}</Badge>
                  </TableCell>
                  <TableCell>{ticket.category}</TableCell>
                  <TableCell>{formatDate(ticket.updated_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}
    </div>
  );
}
