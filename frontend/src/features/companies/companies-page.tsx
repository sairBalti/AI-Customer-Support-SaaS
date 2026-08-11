import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listCompanies } from "@/api/companies";
import { Badge } from "@/components/ui/badge";
import { ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getErrorMessage } from "@/lib/api-error";
import { formatDate } from "@/lib/utils";

export function CompaniesPage() {
  const query = useQuery({
    queryKey: ["companies"],
    queryFn: () => listCompanies({ page: 1, page_size: 50 }),
  });

  return (
    <div>
      <PageHeader title="Companies" description="Tenant companies visible to your account." />
      {query.isLoading ? <LoadingBlock /> : null}
      {query.error ? <ErrorBlock message={getErrorMessage(query.error)} /> : null}
      {query.data ? (
        <div className="rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Slug</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Plan</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data.items.map((company) => (
                <TableRow key={company.company_id}>
                  <TableCell>
                    <Link className="font-medium text-teal-800 hover:underline" to={`/app/companies/${company.company_id}`}>
                      {company.company_name}
                    </Link>
                  </TableCell>
                  <TableCell>{company.company_slug}</TableCell>
                  <TableCell>
                    <Badge>{company.status}</Badge>
                  </TableCell>
                  <TableCell>{company.subscription_plan}</TableCell>
                  <TableCell>{formatDate(company.updated_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}
    </div>
  );
}
