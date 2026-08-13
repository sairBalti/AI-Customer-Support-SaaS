import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Building2,
  ChevronLeft,
  ChevronRight,
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
  superAdminOnly?: boolean;
}

const NAV: NavItem[] = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/companies", label: "Companies", icon: Building2, permissions: ["companies.read"] },
  { to: "/app/users", label: "Users", icon: Users, permissions: ["users.read"] },
  { to: "/app/roles", label: "Roles", icon: Shield, superAdminOnly: true },
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

const SIDEBAR_STORAGE_KEY = "acs_sidebar_collapsed";

export function AppShell() {
  const { user, logout, can, canAny } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1";
  });

  useEffect(() => {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  const items = NAV.filter((item) => {
    if (item.superAdminOnly) return Boolean(user?.is_super_admin);
    if (item.permissions) return can(...item.permissions);
    if (item.anyPermissions) return canAny(...item.anyPermissions);
    return true;
  });

  return (
    <div className="min-h-screen bg-background">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 flex flex-col border-r border-border bg-card transition-[width] duration-200 ease-out",
          collapsed ? "w-[4.5rem]" : "w-64",
        )}
      >
        <div className={cn("border-b border-border", collapsed ? "px-3 py-4" : "px-5 py-5")}>
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-700">
            {collapsed ? "ACS" : "Support Agent"}
          </div>
          {!collapsed ? (
            <div className="mt-1 text-lg font-semibold">AI Customer Support</div>
          ) : null}
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/app"}
                title={collapsed ? item.label : undefined}
                className={({ isActive }) =>
                  cn(
                    "flex items-center rounded-md text-sm font-medium text-slate-600 hover:bg-muted hover:text-foreground",
                    collapsed ? "justify-center px-2 py-2.5" : "gap-3 px-3 py-2",
                    isActive && "bg-accent text-accent-foreground",
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed ? <span className="truncate">{item.label}</span> : null}
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-border p-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full px-0"
            onClick={() => setCollapsed((value) => !value)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
      </aside>

      <div
        className={cn(
          "flex min-h-screen min-w-0 flex-col transition-[padding] duration-200 ease-out",
          collapsed ? "pl-[4.5rem]" : "pl-64",
        )}
      >
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-card px-4 py-3 sm:px-6">
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
