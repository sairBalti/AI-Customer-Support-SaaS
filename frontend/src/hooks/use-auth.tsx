import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import axios from "axios";
import * as authApi from "@/api/auth";
import {
  clearSession,
  getAccessToken,
  getCurrentUser,
  getRefreshToken,
  isAuthenticated,
  setCurrentUser,
  setSession,
  subscribeAuth,
} from "@/lib/auth-store";
import { can, canAny } from "@/lib/permissions";
import type { AuthSession, AuthUser, Permission } from "@/types/api";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
  can: (...permissions: Permission[]) => boolean;
  canAny: (...permissions: Permission[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const baseURL = import.meta.env.VITE_API_BASE_URL || "";

async function restoreSession(): Promise<AuthUser | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  if (!getAccessToken()) {
    const { data } = await axios.post<{ success: boolean; data: AuthSession }>(
      `${baseURL}/api/v1/auth/refresh`,
      { refresh_token: refresh },
    );
    if (!data.success) return null;
    setSession(data.data.tokens, data.data.user);
    return data.data.user;
  }
  return authApi.fetchMe();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(getCurrentUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => subscribeAuth(() => setUser(getCurrentUser())), []);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const me = await restoreSession();
        if (!cancelled) {
          if (me) {
            setCurrentUser(me);
            setUser(me);
          } else {
            clearSession();
          }
        }
      } catch {
        if (!cancelled) clearSession();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const session = await authApi.login(email, password);
    setSession(session.tokens, session.user);
    setUser(session.user);
    return session.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout(getRefreshToken(), true);
    } catch {
      // ignore
    } finally {
      clearSession();
      setUser(null);
    }
  }, []);

  const refreshMe = useCallback(async () => {
    const me = await authApi.fetchMe();
    setCurrentUser(me);
    setUser(me);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: isAuthenticated() && Boolean(user),
      login,
      logout,
      refreshMe,
      can: (...permissions) => can(user, ...permissions),
      canAny: (...permissions) => canAny(user, ...permissions),
    }),
    [user, loading, login, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
