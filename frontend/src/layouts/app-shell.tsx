import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Building2,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  ScrollText,
  Search,
  Shield,
  Ticket,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import type { Permission } from "@/types/api";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  permissions?: Permission[];
  anyPermissions?: Permission[];
}

const NAV: NavItem[] = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/companies", label: "Companies", icon: Building2, permissions: ["companies.read"] },
  { to: "/app/users", label: "Users", icon: Users, permissions: ["users.read"] },
  { to: "/app/roles", label: "Roles", icon: Shield, permissions: ["roles.read"] },
  { to: "/app/documents", label: "Documents", icon: FileText, permissions: ["documents.read"] },
  { to: "/app/knowledge", label: "Knowledge", icon: Search, permissions: ["knowledge.search"] },
  {
    to: "/app/chat",
    label: "Chat",
    icon: MessageSquare,
    anyPermissions: ["chat.start", "chat.read"],
  },
  { to: "/app/tickets", label: "Tickets", icon: Ticket, permissions: ["tickets.read"] },
  { to: "/app/audit", label: "Audit", icon: ScrollText, permissions: ["audit.read"] },
];

export function AppShell() {
  const { user, logout, can, canAny } = useAuth();
  const navigate = useNavigate();

  const items = NAV.filter((item) => {
    if (item.permissions) return can(...item.permissions);
    if (item.anyPermissions) return canAny(...item.anyPermissions);
    return true;
  });

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 border-r border-border bg-card md:flex md:flex-col">
        <div className="border-b border-border px-5 py-5">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-700">
            Support Agent
          </div>
          <div className="mt-1 text-lg font-semibold">AI Customer Support</div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/app"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:bg-muted hover:text-foreground",
                    isActive && "bg-accent text-accent-foreground",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border bg-card px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <div className="truncate text-sm font-medium">
              {user?.display_name || `${user?.first_name} ${user?.last_name}`}
            </div>
            <div className="truncate text-xs text-muted-foreground">
              {user?.role_name}
              {user?.company_id ? ` · Company #${user.company_id}` : null}
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </header>
        <main className="flex-1 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
