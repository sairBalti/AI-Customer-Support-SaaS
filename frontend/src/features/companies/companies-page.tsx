import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowDown, ArrowUp } from "lucide-react";
import { createCompany, listCompanies } from "@/api/companies";
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
import { PhoneInput } from "@/components/ui/phone-input";
import { TimezoneSelect } from "@/components/ui/timezone-select";
import { EmptyState, ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";
import { cn, formatDate } from "@/lib/utils";

const PAGE_SIZE = 20;
const STATUS_OPTIONS = ["", "ACTIVE", "INACTIVE", "SUSPENDED", "TRIAL", "ARCHIVED"] as const;
const PLAN_OPTIONS = ["", "FREE", "STARTER", "PRO", "BUSINESS", "ENTERPRISE"] as const;
const SORT_FIELDS = [
  { value: "created_at", label: "Created" },
  { value: "updated_at", label: "Updated" },
  { value: "company_name", label: "Name" },
  { value: "status", label: "Status" },
  { value: "subscription_plan", label: "Plan" },
] as const;

const createSchema = z.object({
  company_name: z.string().min(3, "Company name must be at least 3 characters").max(150),
  email: z.string().email("Valid email is required"),
  company_slug: z.string().max(150).optional(),
  timezone: z.string().min(1, "Timezone is required"),
  phone: z.string().max(30).optional(),
  subscription_plan: z.enum(["FREE", "STARTER", "PRO", "BUSINESS", "ENTERPRISE"]),
});

type CreateValues = z.infer<typeof createSchema>;
type SortField = (typeof SORT_FIELDS)[number]["value"];

const selectClass =
  "flex h-10 w-full rounded-md border border-border bg-card px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30";

export function CompaniesPage() {
  const { can, user } = useAuth();
  const qc = useQueryClient();
  const canAdd = Boolean(user?.is_super_admin);
  const canManage = can("companies.manage");
  const canEdit = can("companies.update") || canManage;

  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [plan, setPlan] = useState("");
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [sortBy, setSortBy] = useState<SortField>("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [createOpen, setCreateOpen] = useState(false);

  const query = useQuery({
    queryKey: ["companies", page, search, status, plan, includeDeleted, sortBy, sortOrder],
    queryFn: () =>
      listCompanies({
        page,
        page_size: PAGE_SIZE,
        sort_by: sortBy,
        sort_order: sortOrder,
        ...(search ? { search } : {}),
        ...(status ? { status } : {}),
        ...(plan ? { subscription_plan: plan } : {}),
        ...(includeDeleted ? { include_deleted: true } : {}),
      }),
  });

  const form = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      company_name: "",
      email: "",
      company_slug: "",
      timezone: "UTC",
      phone: "",
      subscription_plan: "FREE",
    },
  });

  const createMutation = useMutation({
    mutationFn: (values: CreateValues) =>
      createCompany({
        company_name: values.company_name.trim(),
        email: values.email.trim(),
        company_slug: values.company_slug?.trim() || undefined,
        timezone: values.timezone.trim() || "UTC",
        phone: values.phone?.trim() || undefined,
        subscription_plan: values.subscription_plan,
        activate_trial: false,
      }),
    onSuccess: (company) => {
      toast.success(`${company.company_name} created`);
      setCreateOpen(false);
      form.reset();
      setPage(1);
      void qc.invalidateQueries({ queryKey: ["companies"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const meta = query.data?.meta;
  const items = query.data?.items ?? [];

  const columnSort = useMemo(
    () =>
      (field: SortField) => {
        if (sortBy === field) {
          setSortOrder((current) => (current === "asc" ? "desc" : "asc"));
        } else {
          setSortBy(field);
          setSortOrder(field === "company_name" ? "asc" : "desc");
        }
        setPage(1);
      },
    [sortBy],
  );

  function applySearch() {
    setSearch(searchInput.trim());
    setPage(1);
  }

  return (
    <div>
      <PageHeader
        title="Companies"
        description="Tenant companies visible to your account."
        actions={
          canAdd ? (
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
              <DialogTrigger asChild>
                <Button>Add company</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add company</DialogTitle>
                  <DialogDescription>
                    Registers a new tenant. Slug is generated from the name when omitted.
                  </DialogDescription>
                </DialogHeader>
                <form
                  className="space-y-3"
                  onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
                >
                  <div className="space-y-1">
                    <Label htmlFor="company-name">Company name</Label>
                    <Input id="company-name" {...form.register("company_name")} />
                    {form.formState.errors.company_name ? (
                      <p className="text-xs text-destructive">
                        {form.formState.errors.company_name.message}
                      </p>
                    ) : null}
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="company-email">Ops email</Label>
                    <Input id="company-email" type="email" {...form.register("email")} />
                    {form.formState.errors.email ? (
                      <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
                    ) : null}
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="company-slug">Slug (optional)</Label>
                    <Input id="company-slug" {...form.register("company_slug")} />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="company-timezone">Timezone</Label>
                    <TimezoneSelect
                      id="company-timezone"
                      value={form.watch("timezone")}
                      onChange={(value) =>
                        form.setValue("timezone", value, { shouldValidate: true })
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="company-phone">Phone</Label>
                    <PhoneInput
                      id="company-phone"
                      timezone={form.watch("timezone")}
                      value={form.watch("phone") ?? ""}
                      onChange={(value) => form.setValue("phone", value, { shouldValidate: true })}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="company-plan">Plan</Label>
                    <select
                      id="company-plan"
                      className={selectClass}
                      {...form.register("subscription_plan")}
                    >
                      {PLAN_OPTIONS.filter(Boolean).map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button type="submit" disabled={createMutation.isPending}>
                    {createMutation.isPending ? "Creating…" : "Create company"}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          ) : null
        }
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <div className="space-y-1 sm:col-span-2">
          <Label htmlFor="company-search">Search</Label>
          <div className="flex gap-2">
            <Input
              id="company-search"
              placeholder="Name, slug, or email"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") applySearch();
              }}
            />
            <Button type="button" variant="outline" onClick={applySearch}>
              Search
            </Button>
          </div>
        </div>
        <div className="space-y-1">
          <Label htmlFor="company-status-filter">Status</Label>
          <select
            id="company-status-filter"
            className={selectClass}
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.filter(Boolean).map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="company-plan-filter">Plan</Label>
          <select
            id="company-plan-filter"
            className={selectClass}
            value={plan}
            onChange={(e) => {
              setPlan(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All plans</option>
            {PLAN_OPTIONS.filter(Boolean).map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="company-sort">Sort by</Label>
          <div className="flex gap-2">
            <select
              id="company-sort"
              className={selectClass}
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as SortField);
                setPage(1);
              }}
            >
              {SORT_FIELDS.map((field) => (
                <option key={field.value} value={field.value}>
                  {field.label}
                </option>
              ))}
            </select>
            <select
              aria-label="Sort order"
              className={selectClass}
              value={sortOrder}
              onChange={(e) => {
                setSortOrder(e.target.value as "asc" | "desc");
                setPage(1);
              }}
            >
              <option value="desc">Desc</option>
              <option value="asc">Asc</option>
            </select>
          </div>
        </div>
      </div>

      {canManage ? (
        <label className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={includeDeleted}
            onChange={(e) => {
              setIncludeDeleted(e.target.checked);
              setPage(1);
            }}
          />
          Include deleted
        </label>
      ) : null}

      {query.isLoading ? <LoadingBlock /> : null}
      {query.error ? <ErrorBlock message={getErrorMessage(query.error)} /> : null}
      {query.data && items.length === 0 ? (
        <EmptyState title="No companies found" description="Try a different search or filter." />
      ) : null}
      {query.data && items.length > 0 ? (
        <>
          <div className="rounded-lg border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableHead
                    label="Name"
                    active={sortBy === "company_name"}
                    order={sortOrder}
                    onClick={() => columnSort("company_name")}
                  />
                  <TableHead>Slug</TableHead>
                  <SortableHead
                    label="Status"
                    active={sortBy === "status"}
                    order={sortOrder}
                    onClick={() => columnSort("status")}
                  />
                  <SortableHead
                    label="Plan"
                    active={sortBy === "subscription_plan"}
                    order={sortOrder}
                    onClick={() => columnSort("subscription_plan")}
                  />
                  <TableHead>Email</TableHead>
                  <SortableHead
                    label="Updated"
                    active={sortBy === "updated_at"}
                    order={sortOrder}
                    onClick={() => columnSort("updated_at")}
                  />
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((company) => (
                  <TableRow key={company.company_id} className={company.deleted_at ? "opacity-60" : undefined}>
                    <TableCell>
                      <Link
                        className="font-medium text-teal-800 hover:underline"
                        to={`/app/companies/${company.company_id}`}
                      >
                        {company.company_name}
                      </Link>
                    </TableCell>
                    <TableCell>{company.company_slug}</TableCell>
                    <TableCell>
                      <Badge>{company.status}</Badge>
                    </TableCell>
                    <TableCell>{company.subscription_plan}</TableCell>
                    <TableCell className="max-w-[220px] truncate">{company.email}</TableCell>
                    <TableCell>{formatDate(company.updated_at)}</TableCell>
                    <TableCell className="text-right">
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/app/companies/${company.company_id}`}>
                          {canEdit ? "Edit" : "View"}
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {meta ? (
            <div className="mt-4 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Page {meta.page} of {Math.max(meta.total_pages, 1)} · {meta.total_items} total
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!meta.total_pages || page >= meta.total_pages}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function SortableHead({
  label,
  active,
  order,
  onClick,
}: {
  label: string;
  active: boolean;
  order: "asc" | "desc";
  onClick: () => void;
}) {
  return (
    <TableHead>
      <button
        type="button"
        className={cn(
          "inline-flex items-center gap-1 uppercase tracking-wide",
          active ? "text-foreground" : "text-muted-foreground",
        )}
        onClick={onClick}
      >
        {label}
        {active ? (
          order === "asc" ? (
            <ArrowUp className="h-3 w-3" />
          ) : (
            <ArrowDown className="h-3 w-3" />
          )
        ) : null}
      </button>
    </TableHead>
  );
}
