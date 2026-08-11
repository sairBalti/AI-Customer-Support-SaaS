import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { createRole, deleteRole, listRoles } from "@/api/roles";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
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

const schema = z.object({
  role_name: z.string().min(2),
  display_name: z.string().min(2),
  description: z.string().optional(),
});

type Values = z.infer<typeof schema>;

export function RolesPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const query = useQuery({
    queryKey: ["roles"],
    queryFn: () => listRoles({ page: 1, page_size: 50, include_global: true }),
  });
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { role_name: "", display_name: "", description: "" },
  });

  const createMutation = useMutation({
    mutationFn: (values: Values) => createRole(values),
    onSuccess: () => {
      toast.success("Role created");
      setOpen(false);
      form.reset();
      void qc.invalidateQueries({ queryKey: ["roles"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteRole(id),
    onSuccess: () => {
      toast.success("Role deleted");
      void qc.invalidateQueries({ queryKey: ["roles"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title="Roles"
        description="Company and global roles. Permission assignment is managed by the backend seed."
        actions={
          can("roles.create") ? (
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button>Create role</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create role</DialogTitle>
                </DialogHeader>
                <form
                  className="space-y-3"
                  onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
                >
                  <div className="space-y-1">
                    <Label>Role name</Label>
                    <Input {...form.register("role_name")} />
                  </div>
                  <div className="space-y-1">
                    <Label>Display name</Label>
                    <Input {...form.register("display_name")} />
                  </div>
                  <div className="space-y-1">
                    <Label>Description</Label>
                    <Input {...form.register("description")} />
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
      {query.isLoading ? <LoadingBlock /> : null}
      {query.error ? <ErrorBlock message={getErrorMessage(query.error)} /> : null}
      {query.data ? (
        <div className="rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Display</TableHead>
                <TableHead>Scope</TableHead>
                <TableHead>Active</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data.items.map((role) => (
                <TableRow key={role.role_id}>
                  <TableCell className="font-medium">{role.role_name}</TableCell>
                  <TableCell>{role.display_name}</TableCell>
                  <TableCell>{role.company_id ? `Company #${role.company_id}` : "Global"}</TableCell>
                  <TableCell>
                    <Badge variant={role.is_active ? "success" : "secondary"}>
                      {role.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {can("roles.delete") && !role.is_system_role ? (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => deleteMutation.mutate(role.role_id)}
                      >
                        Delete
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
