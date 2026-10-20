import { apiBase } from "./serverConfig";

const AUTH_TIMEOUT_MS = 12000;

export type AccountUser = {
  id: string;
  identifier: string;
  kind: "email" | "phone";
  name: string;
};

const TOKEN_KEY = "myogaze.token";

export function storedToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function saveToken(token: string) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function readError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string };
    if (typeof data.detail === "string" && data.detail) return data.detail;
  } catch {
    /* ignore */
  }
  return "Could not reach the laptop.";
}

async function authPost(path: string, identifier: string, password: string): Promise<AccountUser> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), AUTH_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${apiBase()}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, password }),
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("The laptop did not answer. Same Wi-Fi, then try again.");
    }
    throw new Error("Could not reach the laptop.");
  } finally {
    window.clearTimeout(timer);
  }
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as { token: string; user: AccountUser };
  saveToken(data.token);
  return data.user;
}

export async function signUp(identifier: string, password: string): Promise<AccountUser> {
  return authPost("/api/auth/register", identifier, password);
}

export async function signIn(identifier: string, password: string): Promise<AccountUser> {
  return authPost("/api/auth/login", identifier, password);
}

export async function currentUser(): Promise<AccountUser | null> {
  const token = storedToken();
  if (!token) return null;
  const res = await fetch(`${apiBase()}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    saveToken("");
    return null;
  }
  const data = (await res.json()) as { user: AccountUser };
  return data.user;
}

export async function signOut(): Promise<void> {
  const token = storedToken();
  saveToken("");
  if (!token) return;
  await fetch(`${apiBase()}/api/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  }).catch(() => undefined);
}
