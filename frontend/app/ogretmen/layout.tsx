"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Me, ReviewQueueItem } from "@/lib/types";
import { cx } from "@/components/ui";

export default function TeacherLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [pendingCount, setPendingCount] = useState<number>(46);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api<Me>("/auth/me").then(setMe).catch(() => undefined);
    api<ReviewQueueItem[]>("/reviews/queue")
      .then((items) => setPendingCount(items.length))
      .catch(() => undefined);
  }, [path]);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/giris");
  }

  const initials = me?.full_name
    ? me.full_name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "DÖ";

  const isSinavlar = path.startsWith("/ogretmen/sinavlar") && !path.includes("yukle");
  const isYukle = path.includes("yukle=1");
  const isInceleme = path.startsWith("/ogretmen/inceleme") || path.startsWith("/ogretmen/analiz");

  return (
    <div className="flex min-h-screen bg-[#f8fafc] text-slate-800 antialiased font-sans">
      {/* Sleek CRM Sidebar (Attio / Linear style) */}
      <aside
        className={cx(
          "fixed inset-y-0 left-0 z-40 w-64 shrink-0 border-r border-slate-200/80 bg-white transition-transform duration-200 ease-out lg:static lg:translate-x-0 flex flex-col justify-between",
          open ? "translate-x-0 shadow-2xl" : "-translate-x-full",
        )}
      >
        <div className="flex flex-col flex-1 overflow-y-auto">
          {/* Workspace Switcher */}
          <div className="p-3">
            <div className="flex items-center justify-between rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5 hover:bg-slate-100/70 transition-colors cursor-pointer group">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-xs shadow-2xs">
                  B
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-bold text-slate-900 truncate tracking-tight">BCN LearnDNA</p>
                  <p className="text-[10px] font-medium text-slate-500 truncate">7-A Matematik Çalışma Alanı</p>
                </div>
              </div>
              <span className="text-slate-400 text-xs">▾</span>
            </div>
          </div>

          {/* Quick Search Bar */}
          <div className="px-3 pb-3">
            <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-400 shadow-2xs">
              <span className="flex items-center gap-1.5">
                <svg className="h-3.5 w-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span>Hızlı Arama...</span>
              </span>
              <kbd className="rounded bg-slate-100 border border-slate-200 px-1.5 py-0.5 text-[9px] font-bold text-slate-500 font-mono">
                ⌘K
              </kbd>
            </div>
          </div>

          {/* Navigation Sections */}
          <div className="px-2 space-y-5">
            {/* Core Module */}
            <div>
              <p className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                ÖLÇME VE HATA ANALİZİ
              </p>
              <nav className="flex flex-col gap-0.5">
                <Link
                  href="/ogretmen/sinavlar"
                  onClick={() => setOpen(false)}
                  className={cx(
                    "flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all cursor-pointer",
                    isSinavlar
                      ? "bg-indigo-50/80 text-indigo-700 font-semibold"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                  )}
                >
                  <span className="flex items-center gap-2">
                    <svg className="h-4 w-4 shrink-0 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>Sınav Yönetimi</span>
                  </span>
                  <span className="rounded bg-slate-100 px-1.5 py-0.2 text-[10px] font-bold text-slate-500">1</span>
                </Link>

                <Link
                  href="/ogretmen/sinavlar?yukle=1"
                  onClick={() => setOpen(false)}
                  className={cx(
                    "flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all cursor-pointer",
                    isYukle
                      ? "bg-indigo-50/80 text-indigo-700 font-semibold"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                  )}
                >
                  <span className="flex items-center gap-2">
                    <svg className="h-4 w-4 shrink-0 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                    <span>Yeni Öğrenci Yükle</span>
                  </span>
                  <span className="rounded bg-indigo-50 border border-indigo-200 text-indigo-700 px-1.5 py-0.2 text-[9px] font-bold">
                    Hızlı
                  </span>
                </Link>

                <Link
                  href="/ogretmen/inceleme"
                  onClick={() => setOpen(false)}
                  className={cx(
                    "flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all cursor-pointer",
                    isInceleme
                      ? "bg-indigo-50/80 text-indigo-700 font-semibold"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                  )}
                >
                  <span className="flex items-center gap-2">
                    <svg className="h-4 w-4 shrink-0 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <span>AI İnceleme Kuyruğu</span>
                  </span>
                  <span className="rounded-full bg-amber-100 border border-amber-200/70 text-amber-800 px-1.5 py-0.2 text-[10px] font-bold tabular-nums">
                    {pendingCount}
                  </span>
                </Link>
              </nav>
            </div>

            {/* Academic CRM Database */}
            <div>
              <p className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                ÖĞRENCİ & SINIF CRM
              </p>
              <nav className="flex flex-col gap-0.5">
                {[
                  { label: "Öğrenci Profilleri", count: "24", icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" },
                  { label: "Sınıflar & Şubeler", count: "2", icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" },
                  { label: "Kazanım Haritası", count: "5", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
                  { label: "Müdahale & Öneriler", badge: "Faz 3", icon: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
                ].map((it) => (
                  <span
                    key={it.label}
                    className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs text-slate-400 select-none cursor-not-allowed opacity-75"
                  >
                    <span className="flex items-center gap-2">
                      <svg className="h-4 w-4 shrink-0 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d={it.icon} />
                      </svg>
                      <span>{it.label}</span>
                    </span>
                    {it.count && (
                      <span className="text-[10px] font-mono text-slate-400">{it.count}</span>
                    )}
                    {it.badge && (
                      <span className="rounded bg-slate-100 px-1 py-0.2 text-[9px] font-bold text-slate-400">
                        {it.badge}
                      </span>
                    )}
                  </span>
                ))}
              </nav>
            </div>
          </div>
        </div>

        {/* User Card at Bottom */}
        <div className="p-3 border-t border-slate-200/80 bg-slate-50/50">
          <div className="flex items-center justify-between gap-2 rounded-xl p-1.5 hover:bg-slate-100/80 transition-colors">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white font-bold text-xs shadow-2xs">
                {initials}
                <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-emerald-500" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-slate-900 truncate">{me?.full_name ?? "Öğretmen"}</p>
                <p className="text-[10px] text-slate-500 truncate">7-A Matematik</p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Çıkış Yap"
              className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Drawer Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/30 backdrop-blur-xs lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Main Content Area */}
      <div className="flex min-w-0 flex-1 flex-col overflow-x-hidden">
        {/* Top Minimal CRM Navbar */}
        <header className="sticky top-0 z-20 flex h-12 items-center justify-between border-b border-slate-200/80 bg-white/90 px-6 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <button
              className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden cursor-pointer"
              onClick={() => setOpen(true)}
              aria-label="Menüyü aç"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
              <span className="text-slate-600 font-semibold">Ölçme & Değerlendirme</span>
              <span>/</span>
              <span className="text-slate-800">
                {isSinavlar ? "Sınav Yönetimi" : isInceleme ? "AI İnceleme Kuyruğu" : "Genel Bakış"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50/80 px-2.5 py-1 text-[11px] font-medium text-slate-600">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Motor 1 Aktif</span>
            </div>
            <Link
              href="/ogretmen/sinavlar?yukle=1"
              className="hidden sm:inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 transition-colors cursor-pointer"
            >
              <span>+ Yeni Yükleme</span>
            </Link>
          </div>
        </header>

        {/* Dynamic Page Container */}
        <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
