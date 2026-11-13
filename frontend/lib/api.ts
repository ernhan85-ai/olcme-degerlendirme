// Browser-side API client. All calls go through the Next.js /api/backend proxy, which attaches
// the JWT from an httpOnly cookie — the token is never readable by page JavaScript.

export class ApiError extends Error {
  constructor(public status: number, message: string, public detail?: unknown) {
    super(message);
  }
}

export function errorMessage(detail: unknown, fallback = "İşlem tamamlanamadı."): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d))).join(" · ");
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    const d = detail as { message: string; blockers?: string[] };
    return d.blockers?.length ? `${d.message} ${d.blockers.join(" ")}` : d.message;
  }
  return fallback;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData;
  const res = await fetch(`/api/backend${path}`, {
    ...init,
    headers: { ...(isForm || !init.body ? {} : { "Content-Type": "application/json" }), ...(init.headers || {}) },
    cache: "no-store",
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = `/giris?next=${encodeURIComponent(window.location.pathname)}`;
  }
  const text = await res.text();
  const data = text ? safeJson(text) : null;
  if (!res.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? (data as { detail: unknown }).detail : data;
    throw new ApiError(res.status, errorMessage(detail), detail);
  }
  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const fileUrl = (fileId: string) => `/api/backend/files/${fileId}`;
