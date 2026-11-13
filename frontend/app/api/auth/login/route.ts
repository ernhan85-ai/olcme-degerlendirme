import { NextResponse } from "next/server";
import { API_URL, COOKIE } from "@/lib/server";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: body.email ?? "", password: body.password ?? "" }),
    cache: "no-store",
  }).catch((err) => {
    console.error("LOGIN FETCH ERROR:", err, "TARGET URL:", `${API_URL}/auth/login`);
    return null;
  });
  if (!res) return NextResponse.json({ detail: "Sunucuya ulaşılamadı." }, { status: 502 });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return NextResponse.json(data, { status: res.status });
  const out = NextResponse.json({ ok: true });
  out.cookies.set(COOKIE, data.access_token, {
    httpOnly: true, sameSite: "lax", secure: false, path: "/", maxAge: 60 * 60,
  });
  return out;
}
