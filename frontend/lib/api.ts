/**
 * Typed client for the MediBot backend.
 *
 * The token is the only thing the frontend stores. It carries the role, and the
 * server re-derives that role on every request - the UI never sends a role, and
 * a role sent in the body would be ignored anyway. Everything the UI displays
 * about permissions is what the server reported, never a local assumption.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "medibot.token";
const SESSION_KEY = "medibot.session";

export type RetrievalType = "hybrid_rag" | "sql_rag" | "blocked";

export interface Source {
  source_document: string;
  section_title: string;
  collection: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  retrieval_type: RetrievalType;
  role: string;
  rerank_scores?: number[] | null;
  sql_query?: string | null;
  blocked: boolean;
}

export interface Session {
  role: string;
  collections: string[];
  sql_access: boolean;
  username: string;
}

export interface Health {
  status: string;
  qdrant: string;
  groq: string;
  collection: string;
  points_count: number;
  model: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

// --- session storage --------------------------------------------------------

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

function storeSession(token: string, session: Session) {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function logout() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(SESSION_KEY);
}

// --- requests ---------------------------------------------------------------

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
    });
  } catch {
    // The backend being down is the most common demo failure. Say so plainly
    // rather than showing a blank screen.
    throw new ApiError(
      `Cannot reach the MediBot API at ${API_URL}. Is the backend running?`,
      0,
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, response.status);
  }

  return (await response.json()) as T;
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function login(username: string, password: string): Promise<Session> {
  const data = await request<{
    access_token: string;
    role: string;
    collections: string[];
    sql_access: boolean;
  }>("/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  const session: Session = {
    role: data.role,
    collections: data.collections,
    sql_access: data.sql_access,
    username,
  };
  storeSession(data.access_token, session);
  return session;
}

export async function ask(question: string): Promise<ChatResponse> {
  // Note: only `question` is sent. There is deliberately no `role` field - the
  // server takes the role from the token, and sending one here would achieve
  // nothing except look like an attempt.
  return request<ChatResponse>("/chat", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ question }),
  });
}

export async function health(): Promise<Health> {
  return request<Health>("/health");
}
