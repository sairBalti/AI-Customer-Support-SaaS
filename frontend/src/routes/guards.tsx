import { Navigate, Outlet, useLocation } from "react-router-dom";
import { LoadingBlock } from "@/components/ui/page";
import { useAuth } from "@/hooks/use-auth";
import type { Permission } from "@/types/api";

export function ProtectedRoute({
  permissions,
  requireAny = false,
}: {
  permissions?: Permission[];
  requireAny?: boolean;
}) {
  const { isAuthenticated, loading, can, canAny } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingBlock label="Checking session…" />;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (permissions && permissions.length > 0) {
    const allowed = requireAny ? canAny(...permissions) : can(...permissions);
    if (!allowed) return <Navigate to="/forbidden" replace />;
  }
  return <Outlet />;
}

export function GuestRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <LoadingBlock />;
  if (isAuthenticated) return <Navigate to="/app" replace />;
  return <Outlet />;
}
