// Authenticated reverse proxy to FastAPI. Reads the JWT from the httpOnly cookie.
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_URL, COOKIE } from "@/lib/server";

type Ctx = { params: Promise<{ path: string[] }> };

async function forward(req: Request, ctx: Ctx) {
  const { path } = await ctx.params;
  if (path.some((p) => p === ".." || p.includes("/"))) return NextResponse.json({ detail: "Geçersiz yol." }, { status: 400 });
  const token = (await cookies()).get(COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: "Oturum açmanız gerekiyor." }, { status: 401 });
  const url = new URL(req.url);
  const target = `${API_URL}/${path.map(encodeURIComponent).join("/")}${url.search}`;
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  const ct = req.headers.get("content-type");
  if (ct) headers["Content-Type"] = ct;
  const hasBody = !["GET", "HEAD"].includes(req.method);
  const res = await fetch(target, {
    method: req.method, headers, body: hasBody ? await req.arrayBuffer() : undefined, cache: "no-store",
  }).catch((err) => {
    console.error("PROXY FETCH ERROR:", err, "TARGET URL:", target);
    return null;
  });
  if (!res) return NextResponse.json({ detail: "Sunucuya ulaşılamadı." }, { status: 502 });
  const out = new NextResponse(res.body, { status: res.status });
  for (const h of ["content-type", "content-disposition", "cache-control"]) {
    const v = res.headers.get(h);
    if (v) out.headers.set(h, v);
  }
  return out;
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const DELETE = forward;
