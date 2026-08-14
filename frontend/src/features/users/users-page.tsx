import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm, type UseFormRegister, type FieldValues } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { listCompanies } from "@/api/companies";
import { listRoles } from "@/api/roles";
import {
  activateUser,
  assignUserCompany,
  createUser,
  deactivateUser,
  listUsers,
  resetUserPassword,
  updateUser,
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
import { PasswordInput } from "@/components/ui/password-input";
import { ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";
import type { ManagedUser } from "@/types/api";

const selectClass =
  "flex h-10 w-full rounded-md border border-border bg-card px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50";

function roleNeedsCompany(roleName: string) {
  return roleName.trim().toUpperCase() !== "SUPER_ADMIN";
}

const createSchema = z
  .object({
    email: z.string().email(),
    password: z.string().min(12),
    first_name: z.string().min(2),
    last_name: z.string().min(2),
    role_name: z.string().min(1, "Select a role"),
    company_id: z.number().int().positive().optional(),
  })
  .superRefine((values, ctx) => {
    if (roleNeedsCompany(values.role_name) && !values.company_id) {
      ctx.addIssue({
        code: "custom",
        path: ["company_id"],
        message: "Select a company",
      });
    }
  });

const editSchema = z.object({
  email: z.string().email(),
  first_name: z.string().min(2),
  last_name: z.string().min(2),
  phone: z.string().max(30).optional(),
  job_title: z.string().max(100).optional(),
  password: z
    .string()
    .optional()
    .refine((value) => !value || value.length >= 12, "At least 12 characters"),
  company_id: z.number().int().positive().optional(),
});

type CreateValues = z.infer<typeof createSchema>;
type EditValues = z.infer<typeof editSchema>;

export function UsersPage() {
  const { can, user } = useAuth();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ManagedUser | null>(null);
  const isSuperAdmin = Boolean(user?.is_super_admin);
  const canCreate = can("users.create");
  const canUpdate = can("users.update");
  const lookupOpen = open || editing !== null;

  const query = useQuery({
    queryKey: ["users"],
    queryFn: () => listUsers({ page: 1, page_size: 50 }),
  });

  const rolesQuery = useQuery({
    queryKey: ["roles", "user-form"],
    queryFn: () => listRoles({ page: 1, page_size: 100, include_global: true, is_active: true }),
    enabled: (canCreate || canUpdate) && lookupOpen,
  });

  const companiesQuery = useQuery({
    queryKey: ["companies", "user-form"],
    queryFn: () =>
      listCompanies({ page: 1, page_size: 100, sort_by: "company_name", sort_order: "asc" }),
    enabled: (canCreate || canUpdate) && lookupOpen,
  });

  const form = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      email: "",
      password: "",
      first_name: "",
      last_name: "",
      role_name: "SUPPORT_AGENT",
      company_id: isSuperAdmin ? undefined : user?.company_id || undefined,
    },
  });

  const editForm = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      email: "",
      first_name: "",
      last_name: "",
      phone: "",
      job_title: "",
      password: "",
      company_id: undefined,
    },
  });

  const selectedRole = form.watch("role_name");
  const showCompany = roleNeedsCompany(selectedRole);
  const showEditCompany = roleNeedsCompany(editing?.role_name || "");

  const roleOptions = useMemo(() => {
    const items = rolesQuery.data?.items ?? [];
    return items
      .filter((role) => !role.deleted_at && role.is_active)
      .filter((role) => isSuperAdmin || role.role_name.toUpperCase() !== "SUPER_ADMIN")
      .sort((a, b) => a.sort_order - b.sort_order || a.display_name.localeCompare(b.display_name));
  }, [isSuperAdmin, rolesQuery.data?.items]);

  const companyOptions = useMemo(() => {
    const items = companiesQuery.data?.items ?? [];
    return items.filter((company) => !company.deleted_at);
  }, [companiesQuery.data?.items]);

  const createMutation = useMutation({
    mutationFn: (values: CreateValues) => {
      const needsCompany = roleNeedsCompany(values.role_name);
      const company_id = needsCompany
        ? isSuperAdmin
          ? values.company_id
          : user?.company_id
        : user?.company_id;
      if (!company_id) {
        throw new Error(
          needsCompany
            ? "Select a company for this role."
            : "Cannot create a Super Admin from this account.",
        );
      }
      return createUser({
        email: values.email,
        password: values.password,
        first_name: values.first_name,
        last_name: values.last_name,
        role_name: values.role_name,
        company_id,
      });
    },
    onSuccess: () => {
      toast.success("User created");
      setOpen(false);
      resetCreateForm();
      void qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const updateMutation = useMutation({
    mutationFn: async (values: EditValues) => {
      if (!editing) throw new Error("No user selected.");
      await updateUser(editing.user_id, {
        email: values.email.trim(),
        first_name: values.first_name.trim(),
        last_name: values.last_name.trim(),
        phone: values.phone?.trim() || null,
        job_title: values.job_title?.trim() || null,
      });
      if (values.password?.trim()) {
        await resetUserPassword(editing.user_id, values.password.trim());
      }
      if (
        isSuperAdmin &&
        roleNeedsCompany(editing.role_name || "") &&
        values.company_id &&
        values.company_id !== editing.company_id
      ) {
        await assignUserCompany(editing.user_id, values.company_id);
      }
    },
    onSuccess: () => {
      toast.success("User updated");
      setEditing(null);
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

  function resetCreateForm() {
    form.reset({
      email: "",
      password: "",
      first_name: "",
      last_name: "",
      role_name: "SUPPORT_AGENT",
      company_id: isSuperAdmin ? undefined : user?.company_id || undefined,
    });
  }

  function openEdit(target: ManagedUser) {
    setEditing(target);
    editForm.reset({
      email: target.email,
      first_name: target.first_name,
      last_name: target.last_name,
      phone: target.phone ?? "",
      job_title: target.job_title ?? "",
      password: "",
      company_id: roleNeedsCompany(target.role_name || "")
        ? target.company_id
        : isSuperAdmin
          ? undefined
          : target.company_id,
    });
  }

  function handleRoleChange(
    role_name: string,
    setRole: (name: string) => void,
    setCompany: (id: number | undefined) => void,
    currentCompanyId?: number,
  ) {
    setRole(role_name);
    if (!roleNeedsCompany(role_name)) {
      setCompany(undefined);
    } else if (!isSuperAdmin && user?.company_id) {
      setCompany(user.company_id);
    } else if (currentCompanyId) {
      setCompany(currentCompanyId);
    }
  }

  return (
    <div>
      <PageHeader
        title="Users"
        description="Manage tenant users and status."
        actions={
          canCreate ? (
            <Dialog
              open={open}
              onOpenChange={(nextOpen) => {
                setOpen(nextOpen);
                if (nextOpen) resetCreateForm();
              }}
            >
              <DialogTrigger asChild>
                <Button>Create user</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create user</DialogTitle>
                  <DialogDescription>
                    Choose a role first. Company is required only for tenant roles.
                  </DialogDescription>
                </DialogHeader>
                <form
                  className="space-y-3"
                  onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
                >
                  <UserIdentityFields
                    prefix="create"
                    register={form.register as unknown as UseFormRegister<FieldValues>}
                    roleName={selectedRole}
                    roleOptions={roleOptions}
                    companyId={form.watch("company_id")}
                    companyOptions={companyOptions}
                    showCompany={showCompany}
                    isSuperAdmin={isSuperAdmin}
                    roleError={form.formState.errors.role_name?.message}
                    companyError={form.formState.errors.company_id?.message}
                    passwordError={form.formState.errors.password?.message}
                    onRoleChange={(role_name) =>
                      handleRoleChange(
                        role_name,
                        (name) => form.setValue("role_name", name, { shouldValidate: true }),
                        (id) => form.setValue("company_id", id, { shouldValidate: true }),
                      )
                    }
                    onCompanyChange={(id) =>
                      form.setValue("company_id", id, { shouldValidate: true })
                    }
                    includePassword
                    includeRole
                  />
                  <Button type="submit" disabled={createMutation.isPending}>
                    {createMutation.isPending ? "Creating…" : "Create"}
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
                <TableHead className="text-right">Actions</TableHead>
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
                    <div className="flex justify-end gap-2">
                      {canUpdate ? (
                        <Button size="sm" variant="outline" onClick={() => openEdit(u)}>
                          Edit
                        </Button>
                      ) : null}
                      {canUpdate ? (
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
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      <Dialog open={editing !== null} onOpenChange={(next) => !next && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit user</DialogTitle>
            <DialogDescription>
              Update profile, password, and company. Leave password blank to keep the current one.
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-3"
            onSubmit={editForm.handleSubmit((values) => updateMutation.mutate(values))}
          >
            <UserIdentityFields
              prefix="edit"
              register={editForm.register as unknown as UseFormRegister<FieldValues>}
              roleName={editing?.role_name || ""}
              roleOptions={roleOptions}
              companyId={editForm.watch("company_id")}
              companyOptions={companyOptions}
              showCompany={showEditCompany}
              isSuperAdmin={isSuperAdmin}
              companyError={editForm.formState.errors.company_id?.message}
              passwordError={editForm.formState.errors.password?.message}
              onRoleChange={() => undefined}
              onCompanyChange={(id) =>
                editForm.setValue("company_id", id, { shouldValidate: true })
              }
              includePassword
            />
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="edit-user-phone">Phone</Label>
                <Input id="edit-user-phone" {...editForm.register("phone")} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="edit-user-job-title">Job title</Label>
                <Input id="edit-user-job-title" {...editForm.register("job_title")} />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving…" : "Save changes"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function UserIdentityFields({
  prefix,
  register,
  roleName,
  roleOptions,
  companyId,
  companyOptions,
  showCompany,
  isSuperAdmin,
  roleError,
  companyError,
  passwordError,
  onRoleChange,
  onCompanyChange,
  includePassword = false,
  includeRole = false,
}: {
  prefix: string;
  register: UseFormRegister<FieldValues>;
  roleName: string;
  roleOptions: Array<{ role_id: number; role_name: string; display_name: string }>;
  companyId?: number;
  companyOptions: Array<{ company_id: number; company_name: string }>;
  showCompany: boolean;
  isSuperAdmin: boolean;
  roleError?: string;
  companyError?: string;
  passwordError?: string;
  onRoleChange: (roleName: string) => void;
  onCompanyChange: (companyId: number | undefined) => void;
  includePassword?: boolean;
  includeRole?: boolean;
}) {
  return (
    <>
      <div className="space-y-1">
        <Label htmlFor={`${prefix}-user-email`}>Email</Label>
        <Input id={`${prefix}-user-email`} {...register("email")} />
      </div>
      {includePassword ? (
        <div className="space-y-1">
          <Label htmlFor={`${prefix}-user-password`}>Password</Label>
          <PasswordInput
            id={`${prefix}-user-password`}
            autoComplete={prefix === "edit" ? "new-password" : "new-password"}
            placeholder={prefix === "edit" ? "Leave blank to keep current password" : undefined}
            {...register("password")}
          />
          <p className="text-xs text-muted-foreground">
            {prefix === "edit"
              ? "Optional. Enter a new password (12+ characters) to reset it."
              : "At least 12 characters."}
          </p>
          {passwordError ? <p className="text-xs text-destructive">{passwordError}</p> : null}
        </div>
      ) : null}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label htmlFor={`${prefix}-user-first-name`}>First name</Label>
          <Input id={`${prefix}-user-first-name`} {...register("first_name")} />
        </div>
        <div className="space-y-1">
          <Label htmlFor={`${prefix}-user-last-name`}>Last name</Label>
          <Input id={`${prefix}-user-last-name`} {...register("last_name")} />
        </div>
      </div>
      {includeRole ? (
        <div className="space-y-1">
          <Label htmlFor={`${prefix}-user-role`}>Role</Label>
          <select
            id={`${prefix}-user-role`}
            className={selectClass}
            value={roleName}
            onChange={(e) => onRoleChange(e.target.value)}
          >
            {roleOptions.length === 0 ? (
              <option value={roleName}>{roleName}</option>
            ) : (
              roleOptions.map((role) => (
                <option key={role.role_id} value={role.role_name}>
                  {role.display_name}
                </option>
              ))
            )}
          </select>
          {roleError ? <p className="text-xs text-destructive">{roleError}</p> : null}
        </div>
      ) : null}
      {showCompany ? (
        <div className="space-y-1">
          <Label htmlFor={`${prefix}-user-company`}>Company</Label>
          <select
            id={`${prefix}-user-company`}
            className={selectClass}
            value={companyId ?? ""}
            disabled={!isSuperAdmin}
            onChange={(e) => onCompanyChange(e.target.value ? Number(e.target.value) : undefined)}
          >
            {isSuperAdmin ? <option value="">Select company</option> : null}
            {companyOptions.map((company) => (
              <option key={company.company_id} value={company.company_id}>
                {company.company_name}
              </option>
            ))}
          </select>
          {companyError ? <p className="text-xs text-destructive">{companyError}</p> : null}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Super Admin is a platform role and is not linked to a company.
        </p>
      )}
    </>
  );
}
