import type { AuthUser, TokenPair } from "@/types/api";

const REFRESH_KEY = "acs_refresh_token";

let accessToken: string | null = null;
let currentUser: AuthUser | null = null;
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

export function subscribeAuth(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getAccessToken() {
  return accessToken;
}

export function getRefreshToken() {
  return sessionStorage.getItem(REFRESH_KEY);
}

export function getCurrentUser() {
  return currentUser;
}

export function setSession(tokens: TokenPair, user: AuthUser) {
  accessToken = tokens.access_token;
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  currentUser = user;
  notify();
}

export function setAccessToken(token: string) {
  accessToken = token;
  notify();
}

export function setCurrentUser(user: AuthUser | null) {
  currentUser = user;
  notify();
}

export function clearSession() {
  accessToken = null;
  currentUser = null;
  sessionStorage.removeItem(REFRESH_KEY);
  notify();
}

export function isAuthenticated() {
  return Boolean(accessToken || getRefreshToken());
}
