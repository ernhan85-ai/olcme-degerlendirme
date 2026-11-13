"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button, ErrorState, Field, inputCls } from "@/components/ui";

function LoginForm() {
  const router = useRouter();
  const next = useSearchParams().get("next") || "/ogretmen/sinavlar";
  const [email, setEmail] = useState("ogretmen@demo.bcn");
  const [password, setPassword] = useState("Demo123!");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    setBusy(false);
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      setErr(typeof d.detail === "string" ? d.detail : "Giriş yapılamadı.");
      return;
    }
    router.replace(next.startsWith("/") && !next.startsWith("//") ? next : "/ogretmen/sinavlar");
  }

  function setDemoAccount(em: string) {
    setEmail(em);
    setPassword("Demo123!");
    setErr(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-xl border border-slate-200/80 bg-slate-50/80 p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Hızlı Demo Girişi (Tek Tıkla Doldur)
        </p>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setDemoAccount("ogretmen@demo.bcn")}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-2xs hover:border-teal-500 hover:text-teal-700 transition-colors cursor-pointer"
          >
            👨‍🏫 7-A Öğretmeni
          </button>
          <button
            type="button"
            onClick={() => setDemoAccount("ogretmen2@demo.bcn")}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-2xs hover:border-teal-500 hover:text-teal-700 transition-colors cursor-pointer"
          >
            👩‍🏫 7-B Öğretmeni
          </button>
          <button
            type="button"
            onClick={() => setDemoAccount("koordinator@demo.bcn")}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-2xs hover:border-teal-500 hover:text-teal-700 transition-colors cursor-pointer"
          >
            🎓 Koordinatör
          </button>
        </div>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label="E-posta Adresi">
          <input
            className={inputCls}
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="ornek@demo.bcn"
          />
        </Field>
        <Field label="Şifre">
          <input
            className={inputCls}
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </Field>
        {err && <ErrorState message={err} />}
        <Button variant="hero" type="submit" loading={busy} className="mt-2 py-3">
          Öğretmen Paneline Giriş Yap →
        </Button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="grid min-h-screen lg:grid-cols-12 bg-white">
      {/* Sol Tanıtım Bölümü */}
      <div className="relative hidden lg:flex lg:col-span-7 flex-col justify-between overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 p-16 text-white">
        {/* Dekoratif Arka Plan Işıkları */}
        <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-teal-500/10 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-indigo-500/15 blur-3xl" />

        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-teal-500/30 bg-teal-950/40 px-3 py-1 text-xs font-medium text-teal-300 backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-teal-400 animate-pulse" />
            Ölçme & Değerlendirme Modülü • LearnDNA 2.0
          </div>
        </div>

        <div className="relative z-10 my-auto max-w-xl">
          <h1 className="font-display text-5xl font-extrabold tracking-tight leading-[1.15] text-white">
            Kanıta Dayalı Ölçme & Bilişsel Hata Muhakemesi
          </h1>
          <p className="mt-5 text-base leading-relaxed text-slate-300 font-normal">
            Öğrencilerin el yazısı çözümlerini adım adım sembolik matematikle doğrulayın; kavram yanılgılarını ve eksik ön koşulları sınav anında tespit edin.
          </p>

          <div className="mt-10 grid gap-3.5">
            <div className="flex items-center gap-3.5 rounded-xl border border-white/10 bg-white/5 p-3.5 backdrop-blur-sm">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-teal-500/20 text-teal-300 font-bold">
                ∑
              </div>
              <div>
                <p className="text-sm font-semibold text-white">SymPy Destekli Matematiksel Doğrulama</p>
                <p className="text-xs text-slate-400">Çözüm zincirindeki işlem ve kural hataları sembolik hesaplama motoruyla kesinleşir.</p>
              </div>
            </div>

            <div className="flex items-center gap-3.5 rounded-xl border border-white/10 bg-white/5 p-3.5 backdrop-blur-sm">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-300 font-bold">
                📊
              </div>
              <div>
                <p className="text-sm font-semibold text-white">Otomatik Madde ve Çeldirici Analizi</p>
                <p className="text-xs text-slate-400">Madde güçlüğü (p), ayırt edicilik (r_pbis), KR-20 ve güvenilirlik göstergeleri.</p>
              </div>
            </div>

            <div className="flex items-center gap-3.5 rounded-xl border border-white/10 bg-white/5 p-3.5 backdrop-blur-sm">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-300 font-bold">
                🎯
              </div>
              <div>
                <p className="text-sm font-semibold text-white">MEB Müfredat Kazanım Haritalaması</p>
                <p className="text-xs text-slate-400">Her soru ilgili kazanıma bağlanır, sınıfın ve öğrencinin kazanım düzeyi ölçülür.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between text-xs text-slate-400 border-t border-white/10 pt-6">
          <p className="tracking-widest uppercase font-semibold text-slate-300">BCN COLLEGE</p>
          <p>© 2026 LearnDNA Platformu</p>
        </div>
      </div>

      {/* Sağ Giriş Formu */}
      <div className="lg:col-span-5 flex items-center justify-center p-8 sm:p-12 lg:p-16 bg-slate-50/50">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <h2 className="font-display text-3xl font-bold tracking-tight text-slate-900">
              Öğretmen Girişi
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              Sınavları yönetmek ve yapay zekâ analizlerini onaylamak için giriş yapın.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200/80 bg-white p-7 shadow-xs">
            <Suspense fallback={<div className="p-4 text-center text-sm text-slate-400">Yükleniyor...</div>}>
              <LoginForm />
            </Suspense>
          </div>
        </div>
      </div>
    </main>
  );
}
