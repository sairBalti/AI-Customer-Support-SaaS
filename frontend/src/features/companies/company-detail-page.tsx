import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  deleteCompany,
  getCompany,
  updateCompany,
  updateCompanyStatus,
  updateCompanySubscription,
} from "@/api/companies";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PhoneInput } from "@/components/ui/phone-input";
import { TimezoneSelect } from "@/components/ui/timezone-select";
import { ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";
import { E164_RE } from "@/lib/phone";
import { formatDate } from "@/lib/utils";

const STATUS_OPTIONS = ["ACTIVE", "INACTIVE", "SUSPENDED", "TRIAL", "ARCHIVED"] as const;
const PLAN_OPTIONS = ["FREE", "STARTER", "PRO", "BUSINESS", "ENTERPRISE"] as const;
const ACTIVATABLE = new Set(["TRIAL", "SUSPENDED", "INACTIVE"]);
const DEACTIVATABLE = new Set(["TRIAL", "ACTIVE", "SUSPENDED"]);

type PendingConfirm =
  | { kind: "activate" }
  | { kind: "deactivate" }
  | { kind: "status"; value: string }
  | { kind: "plan"; value: string }
  | { kind: "delete" };

const editSchema = z.object({
  company_name: z.string().min(3).max(150),
  email: z.string().email(),
  legal_name: z.string().max(200).optional(),
  phone: z
    .string()
    .max(30)
    .optional()
    .refine((value) => !value || E164_RE.test(value), "Enter a valid phone number"),
  website: z.string().max(255).optional(),
  industry: z.string().max(100).optional(),
  country: z.string().max(100).optional(),
  timezone: z.string().min(1).max(100),
});

type EditValues = z.infer<typeof editSchema>;

const selectClass =
  "flex h-10 w-full rounded-md border border-border bg-card px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30";

function emptyToUndefined(value?: string) {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

export function CompanyDetailPage() {
  const { companyId } = useParams();
  const id = Number(companyId);
  const navigate = useNavigate();
  const { can } = useAuth();
  const qc = useQueryClient();
  const [pending, setPending] = useState<PendingConfirm | null>(null);

  const query = useQuery({
    queryKey: ["companies", id],
    queryFn: () => getCompany(id),
    enabled: Number.isFinite(id),
  });

  const form = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      company_name: "",
      email: "",
      legal_name: "",
      phone: "",
      website: "",
      industry: "",
      country: "",
      timezone: "UTC",
    },
  });

  useEffect(() => {
    if (!query.data) return;
    form.reset({
      company_name: query.data.company_name,
      email: query.data.email,
      legal_name: query.data.legal_name ?? "",
      phone: query.data.phone ?? "",
      website: query.data.website ?? "",
      industry: query.data.industry ?? "",
      country: query.data.country ?? "",
      timezone: query.data.timezone,
    });
  }, [form, query.data]);

  const updateMutation = useMutation({
    mutationFn: (values: EditValues) =>
      updateCompany(id, {
        company_name: values.company_name.trim(),
        email: values.email.trim(),
        legal_name: emptyToUndefined(values.legal_name),
        phone: emptyToUndefined(values.phone),
        website: emptyToUndefined(values.website),
        industry: emptyToUndefined(values.industry),
        country: emptyToUndefined(values.country),
        timezone: values.timezone.trim(),
      }),
    onSuccess: () => {
      toast.success("Company updated");
      void qc.invalidateQueries({ queryKey: ["companies"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateCompanyStatus(id, status),
    onSuccess: (_data, status) => {
      toast.success(
        status === "ACTIVE"
          ? "Company activated"
          : status === "INACTIVE"
            ? "Company deactivated"
            : "Status updated",
      );
      setPending(null);
      void qc.invalidateQueries({ queryKey: ["companies"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const planMutation = useMutation({
    mutationFn: (subscription_plan: string) =>
      updateCompanySubscription(id, { subscription_plan }),
    onSuccess: () => {
      toast.success("Subscription updated");
      setPending(null);
      void qc.invalidateQueries({ queryKey: ["companies"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteCompany(id),
    onSuccess: () => {
      toast.success("Company deleted");
      setPending(null);
      void qc.invalidateQueries({ queryKey: ["companies"] });
      navigate("/app/companies");
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  if (query.isLoading) return <LoadingBlock />;
  if (query.error) return <ErrorBlock message={getErrorMessage(query.error)} />;
  if (!query.data) return null;
  const company = query.data;
  const canUpdate = can("companies.update");
  const canManage = can("companies.manage");
  const isDeleted = Boolean(company.deleted_at);
  const isArchived = company.status === "ARCHIVED";
  const canActivate = canManage && !isDeleted && !isArchived && ACTIVATABLE.has(company.status);
  const canDeactivate =
    canManage && !isDeleted && !isArchived && DEACTIVATABLE.has(company.status);
  const confirmBusy = statusMutation.isPending || planMutation.isPending || deleteMutation.isPending;
  const confirmCopy = pending ? confirmDialogCopy(pending, company.company_name, company) : null;

  return (
    <div>
      <PageHeader
        title={company.company_name}
        description={canUpdate || canManage ? "Edit company details, status, and plan." : company.email}
        actions={
          <div className="flex items-center gap-2">
            <Badge>{company.status}</Badge>
            {canActivate ? (
              <Button size="sm" onClick={() => setPending({ kind: "activate" })}>
                Activate
              </Button>
            ) : null}
            {canDeactivate ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setPending({ kind: "deactivate" })}
              >
                Deactivate
              </Button>
            ) : null}
            <Button asChild variant="outline" size="sm">
              <Link to="/app/companies">Back to list</Link>
            </Button>
          </div>
        }
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{canUpdate ? "Edit profile" : "Profile"}</CardTitle>
          </CardHeader>
          <CardContent>
            {canUpdate ? (
              <form
                className="space-y-3"
                onSubmit={form.handleSubmit((values) => updateMutation.mutate(values))}
              >
                <div className="space-y-1">
                  <Label htmlFor="edit-company-name">Company name</Label>
                  <Input id="edit-company-name" {...form.register("company_name")} />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="edit-company-email">Email</Label>
                  <Input id="edit-company-email" type="email" {...form.register("email")} />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="edit-legal-name">Legal name</Label>
                  <Input id="edit-legal-name" {...form.register("legal_name")} />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="edit-timezone">Timezone</Label>
                  <TimezoneSelect
                    id="edit-timezone"
                    value={form.watch("timezone")}
                    onChange={(value) =>
                      form.setValue("timezone", value, { shouldValidate: true })
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="edit-phone">Phone</Label>
                  <PhoneInput
                    id="edit-phone"
                    timezone={form.watch("timezone")}
                    value={form.watch("phone") ?? ""}
                    onChange={(value) => form.setValue("phone", value, { shouldValidate: true })}
                  />
                  {form.formState.errors.phone ? (
                    <p className="text-xs text-destructive">{form.formState.errors.phone.message}</p>
                  ) : null}
                </div>
                <div className="space-y-1">
                  <Label htmlFor="edit-website">Website</Label>
                  <Input id="edit-website" placeholder="https://example.com" {...form.register("website")} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="edit-industry">Industry</Label>
                    <Input id="edit-industry" {...form.register("industry")} />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="edit-country">Country</Label>
                    <Input id="edit-country" {...form.register("country")} />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">Slug: {company.company_slug}</p>
                <Button type="submit" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? "Saving…" : "Save changes"}
                </Button>
              </form>
            ) : (
              <div className="space-y-2 text-sm">
                <Row label="Slug" value={company.company_slug} />
                <Row label="Plan" value={company.subscription_plan} />
                <Row label="Timezone" value={company.timezone} />
                <Row label="Phone" value={company.phone ?? "—"} />
                <Row label="Updated" value={formatDate(company.updated_at)} />
              </div>
            )}
          </CardContent>
        </Card>

        {canManage ? (
          <Card>
            <CardHeader>
              <CardTitle>Manage</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  disabled={!canActivate || statusMutation.isPending}
                  onClick={() => setPending({ kind: "activate" })}
                >
                  Activate
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={!canDeactivate || statusMutation.isPending}
                  onClick={() => setPending({ kind: "deactivate" })}
                >
                  Deactivate
                </Button>
              </div>
              {isArchived ? (
                <p className="text-sm text-muted-foreground">
                  Archived companies cannot be activated or deactivated.
                </p>
              ) : null}
              <div className="space-y-1">
                <Label htmlFor="manage-status">Status</Label>
                <select
                  id="manage-status"
                  className={selectClass}
                  value={company.status}
                  disabled={statusMutation.isPending || isDeleted}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value === company.status) return;
                    setPending({ kind: "status", value });
                  }}
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="manage-plan">Subscription plan</Label>
                <select
                  id="manage-plan"
                  className={selectClass}
                  value={company.subscription_plan}
                  disabled={planMutation.isPending || isDeleted}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value === company.subscription_plan) return;
                    setPending({ kind: "plan", value });
                  }}
                >
                  {PLAN_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
              <Row label="Updated" value={formatDate(company.updated_at)} />
              {!isDeleted ? (
                <Button variant="destructive" onClick={() => setPending({ kind: "delete" })}>
                  Delete company
                </Button>
              ) : (
                <p className="text-sm text-muted-foreground">This company is already deleted.</p>
              )}
            </CardContent>
          </Card>
        ) : null}
      </div>

      <Dialog open={pending !== null} onOpenChange={(open) => !open && !confirmBusy && setPending(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{confirmCopy?.title}</DialogTitle>
            <DialogDescription>{confirmCopy?.description}</DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={confirmBusy}
              onClick={() => setPending(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant={confirmCopy?.destructive ? "destructive" : "default"}
              disabled={confirmBusy}
              onClick={() => {
                if (!pending) return;
                if (pending.kind === "activate") statusMutation.mutate("ACTIVE");
                else if (pending.kind === "deactivate") statusMutation.mutate("INACTIVE");
                else if (pending.kind === "status") statusMutation.mutate(pending.value);
                else if (pending.kind === "plan") planMutation.mutate(pending.value);
                else deleteMutation.mutate();
              }}
            >
              {confirmBusy ? "Working…" : confirmCopy?.confirmLabel}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border py-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function confirmDialogCopy(
  pending: PendingConfirm,
  name: string,
  company: { status: string; subscription_plan: string },
) {
  if (pending.kind === "activate") {
    return {
      title: "Activate company?",
      description: `Activate ${name}? Users in this tenant will be able to sign in and use the platform.`,
      confirmLabel: "Activate",
      destructive: false,
    };
  }
  if (pending.kind === "deactivate") {
    return {
      title: "Deactivate company?",
      description: `Deactivate ${name}? Users in this tenant will not be able to use the platform until it is activated again.`,
      confirmLabel: "Deactivate",
      destructive: true,
    };
  }
  if (pending.kind === "status") {
    return {
      title: "Change company status?",
      description: `Change ${name} from ${company.status} to ${pending.value}?`,
      confirmLabel: "Change status",
      destructive: pending.value === "ARCHIVED" || pending.value === "INACTIVE",
    };
  }
  if (pending.kind === "plan") {
    return {
      title: "Change subscription plan?",
      description: `Change ${name} from ${company.subscription_plan} to ${pending.value}?`,
      confirmLabel: "Change plan",
      destructive: false,
    };
  }
  return {
    title: "Delete company?",
    description: `Soft-delete ${name}. This does not permanently remove the tenant.`,
    confirmLabel: "Delete",
    destructive: true,
  };
}
