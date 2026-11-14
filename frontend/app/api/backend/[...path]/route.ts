// Authenticated reverse proxy to FastAPI with built-in Standalone Demo Mode for Vercel.
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_URL, COOKIE } from "@/lib/server";
import mockDataRaw from "@/lib/mock-data.json";

type Ctx = { params: Promise<{ path: string[] }> };

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockData: any = mockDataRaw;

function getSampleSvgPaper() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1130" viewBox="0 0 800 1130">
    <rect width="800" height="1130" fill="#fdfbf7"/>
    <rect x="30" y="30" width="740" height="1070" fill="none" stroke="#e2e8f0" stroke-width="2"/>
    <text x="50" y="70" font-family="sans-serif" font-size="20" font-weight="bold" fill="#1e293b">BCN COLLEGE — 7. SINIF MATEMATİK 1. DÖNEM 1. YAZILI</text>
    <line x1="50" y1="85" x2="750" y2="85" stroke="#cbd5e1" stroke-width="1.5"/>
    <text x="50" y="115" font-family="sans-serif" font-size="14" fill="#475569">Öğrenci: Ada Yılmaz | No: 1001 | Sınıf: 7-A</text>
    
    <rect x="50" y="145" width="700" height="180" rx="6" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="65" y="175" font-family="sans-serif" font-size="14" font-weight="bold" fill="#0f172a">Soru 1: 3x + 5 = 20 denklemini çözünüz. (20 Puan)</text>
    <text x="80" y="220" font-family="cursive, sans-serif" font-size="18" fill="#1e3a8a">3x + 5 = 20</text>
    <text x="80" y="255" font-family="cursive, sans-serif" font-size="18" fill="#1e3a8a">3x = 20 - 5 = 15</text>
    <text x="80" y="290" font-family="cursive, sans-serif" font-size="18" fill="#1e3a8a">x = 5  [Cevap: 5]</text>

    <rect x="50" y="345" width="700" height="180" rx="6" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="65" y="375" font-family="sans-serif" font-size="14" font-weight="bold" fill="#0f172a">Soru 2: 2(x + 3) = 10 denklemini çözünüz. (20 Puan)</text>
    <text x="80" y="420" font-family="cursive, sans-serif" font-size="18" fill="#1e3a8a">2(x + 3) = 10</text>
    <text x="80" y="455" font-family="cursive, sans-serif" font-size="18" fill="#dc2626">2x + 3 = 10  (Parantez dağıtma hatası)</text>
    <text x="80" y="490" font-family="cursive, sans-serif" font-size="18" fill="#dc2626">2x = 7 => x = 7/2</text>

    <rect x="50" y="545" width="700" height="180" rx="6" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="65" y="575" font-family="sans-serif" font-size="14" font-weight="bold" fill="#0f172a">Soru 3: 1/2 + 1/3 işleminin sonucunu bulunuz. (20 Puan)</text>
    <text x="80" y="620" font-family="cursive, sans-serif" font-size="18" fill="#1e3a8a">1/2(3) + 1/3(2) = 3/6 + 2/6 = 5/6</text>
  </svg>`;
}

async function forward(req: Request, ctx: Ctx) {
  const { path } = await ctx.params;
  if (path.some((p) => p === ".." || p.includes("/"))) {
    return NextResponse.json({ detail: "Geçersiz yol." }, { status: 400 });
  }

  const token = (await cookies()).get(COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Oturum açmanız gerekiyor." }, { status: 401 });
  }

  const pathStr = path.join("/");
  const url = new URL(req.url);

  // 1. If backend URL is explicitly configured AND we are not in a demo session, forward to backend
  if (!token.startsWith("demo_token_") && process.env.LEARNDNA_API_URL) {
    const target = `${API_URL}/${path.map(encodeURIComponent).join("/")}${url.search}`;
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    const ct = req.headers.get("content-type");
    if (ct) headers["Content-Type"] = ct;
    const hasBody = !["GET", "HEAD"].includes(req.method);

    const res = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      cache: "no-store",
    }).catch(() => null);

    if (res && res.ok) {
      const out = new NextResponse(res.body, { status: res.status });
      for (const h of ["content-type", "content-disposition", "cache-control"]) {
        const v = res.headers.get(h);
        if (v) out.headers.set(h, v);
      }
      return out;
    }
  }

  // 2. Standalone Demo Mode Fallback (Works autonomously on Vercel without a backend)
  if (pathStr === "auth/me") {
    const is7B = token.includes("ogretmen2");
    const isCoord = token.includes("koordinator");
    return NextResponse.json({
      id: is7B ? "22222222-2222-2222-2222-222222222222" : isCoord ? "33333333-3333-3333-3333-333333333333" : mockData.me.id,
      full_name: is7B ? "Fatma Demir (7-B Matematik)" : isCoord ? "Mehmet Çelik (Koordinatör)" : mockData.me.full_name,
      email: is7B ? "ogretmen2@demo.bcn" : isCoord ? "koordinator@demo.bcn" : "ogretmen@demo.bcn",
      roles: isCoord ? ["coordinator"] : ["teacher"],
    });
  }

  if (pathStr === "meta/lookups") {
    return NextResponse.json(mockData.lookups);
  }

  if (pathStr === "reviews/queue") {
    return NextResponse.json(mockData.reviews_queue);
  }

  if (pathStr === "exams") {
    return NextResponse.json(mockData.exams);
  }

  if (pathStr.startsWith("exams/")) {
    if (path.length === 2) {
      return NextResponse.json(mockData.exam_detail);
    }
    if (path[2] === "submissions") {
      return NextResponse.json(mockData.submissions);
    }
    if (path[2] === "item-analysis") {
      return NextResponse.json(mockData.item_analysis);
    }
    if (path[2] === "outcome-report") {
      return NextResponse.json(mockData.outcome_report);
    }
    if (["questions", "validate-keys", "publish"].includes(path[2])) {
      return NextResponse.json(mockData.exam_detail);
    }
  }

  if (pathStr.startsWith("submissions/")) {
    if (pathStr.endsWith("/responses")) {
      return NextResponse.json(mockData.sub_responses);
    }
    if (pathStr.endsWith("/retry")) {
      return NextResponse.json(mockData.submissions[0]);
    }
    return NextResponse.json(mockData.submissions[0]);
  }

  if (pathStr.startsWith("responses/")) {
    const rid = path[1];
    const resp = mockData.responses[rid] || Object.values(mockData.responses)[0];
    if (req.method === "POST" && pathStr.endsWith("/score")) {
      const body = await req.json().catch(() => ({}));
      return NextResponse.json({ ...resp, score: body.score ?? resp.score });
    }
    if (req.method === "PUT" && pathStr.endsWith("/transcription")) {
      return NextResponse.json(resp);
    }
    return NextResponse.json(resp);
  }

  if (pathStr.startsWith("hypotheses/")) {
    const resp = Object.values(mockData.responses)[0];
    return NextResponse.json(resp);
  }

  if (pathStr.startsWith("files/")) {
    return new NextResponse(getSampleSvgPaper(), {
      headers: {
        "Content-Type": "image/svg+xml",
        "Cache-Control": "public, max-age=3600",
      },
    });
  }

  return NextResponse.json({ detail: "Bulunamadı" }, { status: 404 });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const DELETE = forward;
