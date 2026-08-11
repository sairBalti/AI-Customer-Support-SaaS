import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getCompany, updateCompanyStatus, updateCompanySubscription } from "@/api/companies";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";
import { formatDate } from "@/lib/utils";

export function CompanyDetailPage() {
  const { companyId } = useParams();
  const id = Number(companyId);
  const { can } = useAuth();
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["companies", id],
    queryFn: () => getCompany(id),
    enabled: Number.isFinite(id),
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateCompanyStatus(id, status),
    onSuccess: () => {
      toast.success("Status updated");
      void qc.invalidateQueries({ queryKey: ["companies", id] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const planMutation = useMutation({
    mutationFn: (subscription_plan: string) =>
      updateCompanySubscription(id, { subscription_plan }),
    onSuccess: () => {
      toast.success("Subscription updated");
      void qc.invalidateQueries({ queryKey: ["companies", id] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  if (query.isLoading) return <LoadingBlock />;
  if (query.error) return <ErrorBlock message={getErrorMessage(query.error)} />;
  if (!query.data) return null;
  const company = query.data;

  return (
    <div>
      <PageHeader
        title={company.company_name}
        description={company.email}
        actions={<Badge>{company.status}</Badge>}
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Slug" value={company.company_slug} />
            <Row label="Plan" value={company.subscription_plan} />
            <Row label="Timezone" value={company.timezone} />
            <Row label="Updated" value={formatDate(company.updated_at)} />
          </CardContent>
        </Card>
        {can("companies.manage") ? (
          <Card>
            <CardHeader>
              <CardTitle>Manage</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => statusMutation.mutate("ACTIVE")}>
                Set ACTIVE
              </Button>
              <Button variant="outline" onClick={() => statusMutation.mutate("SUSPENDED")}>
                Set SUSPENDED
              </Button>
              <Button variant="secondary" onClick={() => planMutation.mutate("PRO")}>
                Plan PRO
              </Button>
              <Button variant="secondary" onClick={() => planMutation.mutate("FREE")}>
                Plan FREE
              </Button>
            </CardContent>
          </Card>
        ) : null}
      </div>
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
