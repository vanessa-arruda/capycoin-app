const TOKEN_KEY = "capycoin_token";
const ROLE_KEY = "capycoin_role";

export type Role = "parent" | "child";

export function saveSession(token: string, role: Role) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRole(): Role | null {
  return localStorage.getItem(ROLE_KEY) as Role | null;
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
