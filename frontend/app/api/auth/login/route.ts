import { NextResponse } from "next/server";
import { API_URL, COOKIE } from "@/lib/server";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const email = (body.email ?? "").trim();
  const password = body.password ?? "";

  // 1. If backend URL is explicitly configured, attempt real backend login
  if (process.env.LEARNDNA_API_URL) {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    }).catch((err) => {
      console.error("LOGIN FETCH ERROR:", err, "TARGET URL:", `${API_URL}/auth/login`);
      return null;
    });

    if (res && res.ok) {
      const data = await res.json().catch(() => ({}));
      const out = NextResponse.json({ ok: true });
      out.cookies.set(COOKIE, data.access_token, {
        httpOnly: true, sameSite: "lax", secure: false, path: "/", maxAge: 60 * 60,
      });
      return out;
    }
  }

  // 2. Demo fallback (for Vercel deployment or standalone testing)
  if (email.endsWith("@demo.bcn") && password === "Demo123!") {
    const out = NextResponse.json({ ok: true });
    out.cookies.set(COOKIE, `demo_token_${email}`, {
      httpOnly: true, sameSite: "lax", secure: false, path: "/", maxAge: 60 * 60,
    });
    return out;
  }

  return NextResponse.json({ detail: "Geçersiz e-posta veya şifre." }, { status: 401 });
}
