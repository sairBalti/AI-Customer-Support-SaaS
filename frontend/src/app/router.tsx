import { Navigate, Route, Routes } from "react-router-dom";
import { AuditPage } from "@/features/audit/audit-page";
import { LoginPage } from "@/features/auth/login-page";
import { RegisterCompanyPage } from "@/features/auth/register-page";
import { ChatPage } from "@/features/chat/chat-page";
import { CompaniesPage } from "@/features/companies/companies-page";
import { CompanyDetailPage } from "@/features/companies/company-detail-page";
import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { DocumentsPage } from "@/features/documents/documents-page";
import { KnowledgePage } from "@/features/knowledge/knowledge-page";
import { MarketingPage } from "@/features/marketing/marketing-page";
import { RolesPage } from "@/features/roles/roles-page";
import { TicketDetailPage } from "@/features/tickets/ticket-detail-page";
import { TicketsPage } from "@/features/tickets/tickets-page";
import { UsersPage } from "@/features/users/users-page";
import { AppShell } from "@/layouts/app-shell";
import { GuestRoute, ProtectedRoute } from "@/routes/guards";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

function ForbiddenPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
      <h1 className="text-2xl font-semibold">403 — Forbidden</h1>
      <p className="text-sm text-muted-foreground">You do not have permission to view this page.</p>
      <Button asChild>
        <Link to="/app">Back to dashboard</Link>
      </Button>
    </div>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<MarketingPage />} />

      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterCompanyPage />} />
      </Route>

      <Route path="/forbidden" element={<ForbiddenPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/app" element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route element={<ProtectedRoute permissions={["companies.read"]} />}>
            <Route path="companies" element={<CompaniesPage />} />
            <Route path="companies/:companyId" element={<CompanyDetailPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={["users.read"]} />}>
            <Route path="users" element={<UsersPage />} />
          </Route>
          <Route element={<ProtectedRoute requireSuperAdmin />}>
            <Route path="roles" element={<RolesPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={["documents.read"]} />}>
            <Route path="documents" element={<DocumentsPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={["knowledge.search"]} />}>
            <Route path="knowledge" element={<KnowledgePage />} />
          </Route>
          <Route
            element={
              <ProtectedRoute permissions={["chat.start", "chat.read"]} requireAny />
            }
          >
            <Route path="chat" element={<ChatPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={["tickets.read"]} />}>
            <Route path="tickets" element={<TicketsPage />} />
            <Route path="tickets/:ticketId" element={<TicketDetailPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={["audit.read"]} />}>
            <Route path="audit" element={<AuditPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
