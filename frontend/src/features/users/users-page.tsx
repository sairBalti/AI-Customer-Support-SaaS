import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  activateUser,
  createUser,
  deactivateUser,
  listUsers,
} from "@/api/users";
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
import { ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";

const createSchema = z.object({
  email: z.string().email(),
  password: z.string().min(12),
  first_name: z.string().min(2),
  last_name: z.string().min(2),
  role_name: z.string().min(1),
  company_id: z.number().int().positive(),
});

type CreateValues = z.infer<typeof createSchema>;

export function UsersPage() {
  const { can, user } = useAuth();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const isSuperAdmin = Boolean(user?.is_super_admin);
  const hasCompanyId = Boolean(user?.company_id);
  const canSubmitCreate = isSuperAdmin || hasCompanyId;

  const query = useQuery({
    queryKey: ["users"],
    queryFn: () => listUsers({ page: 1, page_size: 50 }),
  });

  const form = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      email: "",
      password: "",
      first_name: "",
      last_name: "",
      role_name: "SUPPORT_AGENT",
      company_id: user?.company_id || undefined,
    },
  });

  const createMutation = useMutation({
    mutationFn: (values: CreateValues) => {
      const company_id = isSuperAdmin ? values.company_id : user?.company_id;
      if (!company_id) {
        throw new Error("Company ID is required to create a user.");
      }
      return createUser({ ...values, company_id });
    },
    onSuccess: () => {
      toast.success("User created");
      setOpen(false);
      form.reset({
        email: "",
        password: "",
        first_name: "",
        last_name: "",
        role_name: "SUPPORT_AGENT",
        company_id: user?.company_id || undefined,
      });
      void qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const toggleMutation = useMutation({
    mutationFn: async ({ id, activate }: { id: number; activate: boolean }) =>
      activate ? activateUser(id) : deactivateUser(id),
    onSuccess: () => {
      toast.success("User status updated");
      void qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title="Users"
        description="Manage tenant users and status."
        actions={
          can("users.create") ? (
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button>Create user</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create user</DialogTitle>
                  <DialogDescription>Requires a strong password (12+ characters).</DialogDescription>
                </DialogHeader>
                <form
                  className="space-y-3"
                  onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
                >
                  <div className="space-y-1">
                    <Label>Email</Label>
                    <Input {...form.register("email")} />
                  </div>
                  <div className="space-y-1">
                    <Label>Password</Label>
                    <Input type="password" {...form.register("password")} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label>First name</Label>
                      <Input {...form.register("first_name")} />
                    </div>
                    <div className="space-y-1">
                      <Label>Last name</Label>
                      <Input {...form.register("last_name")} />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label>Role name</Label>
                    <Input {...form.register("role_name")} />
                  </div>
                  {isSuperAdmin ? (
                    <div className="space-y-1">
                      <Label>Company ID</Label>
                      <Input
                        type="number"
                        {...form.register("company_id", { valueAsNumber: true })}
                      />
                    </div>
                  ) : !hasCompanyId ? (
                    <p className="text-sm text-destructive">
                      Your account has no company_id; cannot create users.
                    </p>
                  ) : (
                    <input type="hidden" {...form.register("company_id", { valueAsNumber: true })} />
                  )}
                  <Button
                    type="submit"
                    disabled={createMutation.isPending || !canSubmitCreate}
                  >
                    Create
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          ) : null
        }
      />
      {query.isLoading ? <LoadingBlock /> : null}
      {query.error ? <ErrorBlock message={getErrorMessage(query.error)} /> : null}
      {query.data ? (
        <div className="rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data.items.map((u) => (
                <TableRow key={u.user_id}>
                  <TableCell className="font-medium">
                    {u.first_name} {u.last_name}
                  </TableCell>
                  <TableCell>{u.email}</TableCell>
                  <TableCell>{u.role_name}</TableCell>
                  <TableCell>
                    <Badge>{u.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {can("users.update") ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          toggleMutation.mutate({
                            id: u.user_id,
                            activate: u.status !== "ACTIVE",
                          })
                        }
                      >
                        {u.status === "ACTIVE" ? "Deactivate" : "Activate"}
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}
    </div>
  );
}
