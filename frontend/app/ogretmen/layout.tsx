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
      {/* Sleek Enterprise Sidebar */}
      <aside
        className={cx(
          "fixed inset-y-0 left-0 z-40 w-72 shrink-0 border-r border-slate-200/90 bg-white transition-transform duration-200 ease-out lg:static lg:translate-x-0 flex flex-col justify-between shadow-xs",
          open ? "translate-x-0 shadow-2xl" : "-translate-x-full",
        )}
      >
        <div className="flex flex-col flex-1 overflow-y-auto">
          {/* Workspace Switcher */}
          <div className="p-4 border-b border-slate-100">
            <div className="flex items-center justify-between rounded-2xl border border-slate-200/90 bg-slate-50/80 p-3 hover:bg-slate-100/80 transition-colors cursor-pointer group">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white font-extrabold text-sm shadow-xs">
                  B
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-bold text-slate-900 truncate tracking-tight">BCN LearnDNA</p>
                  <p className="text-xs font-medium text-slate-500 truncate">7-A Matematik Portalı</p>
                </div>
              </div>
              <span className="text-slate-400 text-sm">▾</span>
            </div>
          </div>

          {/* Navigation Sections */}
          <div className="p-4 space-y-6">
            {/* Core Module */}
            <div>
              <p className="px-3 pb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                ÖLÇME VE HATA ANALİZİ
              </p>
              <nav className="flex flex-col gap-1.5">
                <Link
                  href="/ogretmen/sinavlar"
                  onClick={() => setOpen(false)}
                  className={cx(
                    "flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all cursor-pointer",
                    isSinavlar
                      ? "bg-indigo-50 text-indigo-700 shadow-2xs"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                  )}
                >
                  <span className="flex items-center gap-3">
                    <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    <span>Sınav Yönetimi</span>
                  </span>
                  <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-600 tabular-nums">
                    1
                  </span>
                </Link>

                <Link
                  href="/ogretmen/sinavlar?yukle=1"
                  onClick={() => setOpen(false)}
                  className={cx(
                    "flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all cursor-pointer",
                    isYukle
                      ? "bg-indigo-50 text-indigo-700 shadow-2xs"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                  )}
                >
                  <span className="flex items-center gap-3">
                    <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                    <span>Yeni Kâğıt Yükle</span>
                  </span>
                  <span className="rounded-md bg-indigo-100 px-2 py-0.5 text-[11px] font-bold text-indigo-800">
                    HIZLI
                  </span>
                </Link>

                <Link
                  href="/ogretmen/inceleme"
                  onClick={() => setOpen(false)}
                  className={cx(
                    "flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all cursor-pointer",
                    isInceleme
                      ? "bg-indigo-50 text-indigo-700 shadow-2xs"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                  )}
                >
                  <span className="flex items-center gap-3">
                    <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                      />
                    </svg>
                    <span>İnceleme Kuyruğu</span>
                  </span>
                  {pendingCount > 0 && (
                    <span className="rounded-full bg-amber-500 px-2 py-0.5 text-xs font-black text-white tabular-nums shadow-xs">
                      {pendingCount}
                    </span>
                  )}
                </Link>
              </nav>
            </div>

            {/* Platform Modules */}
            <div>
              <p className="px-3 pb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                BCN DİĞER MODÜLLER
              </p>
              <nav className="flex flex-col gap-1 text-sm font-medium text-slate-500">
                <div className="flex items-center justify-between rounded-xl px-3.5 py-2 hover:bg-slate-50 opacity-60 cursor-not-allowed">
                  <span>Öğrenci Karneleri</span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">YAKINDA</span>
                </div>
                <div className="flex items-center justify-between rounded-xl px-3.5 py-2 hover:bg-slate-50 opacity-60 cursor-not-allowed">
                  <span>Soru Havuzu</span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">MEB 2026</span>
                </div>
                <div className="flex items-center justify-between rounded-xl px-3.5 py-2 hover:bg-slate-50 opacity-60 cursor-not-allowed">
                  <span>Müfredat Haritası</span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">M.7.2</span>
                </div>
              </nav>
            </div>
          </div>
        </div>

        {/* User Card at Bottom */}
        <div className="p-4 border-t border-slate-200/80 bg-slate-50/70">
          <div className="flex items-center justify-between gap-3 rounded-2xl p-2 hover:bg-slate-100 transition-colors">
            <div className="flex items-center gap-3 min-w-0">
              <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white font-extrabold text-sm shadow-xs">
                {initials}
                <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-slate-900 truncate">{me?.full_name ?? "Ahmet Yılmaz"}</p>
                <p className="text-xs text-slate-500 truncate">7-A Matematik Öğretmeni</p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Çıkış Yap"
              className="p-2 text-slate-400 hover:text-rose-600 rounded-xl hover:bg-rose-50 transition-colors cursor-pointer"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
        {/* Top Minimal Header */}
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/95 px-6 lg:px-10 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <button
              className="rounded-xl p-2 text-slate-600 hover:bg-slate-100 lg:hidden cursor-pointer"
              onClick={() => setOpen(true)}
              aria-label="Menüyü aç"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="flex items-center gap-2.5 text-sm text-slate-400 font-medium">
              <span className="text-slate-700 font-bold">Ölçme & Değerlendirme</span>
              <span>/</span>
              <span className="text-slate-900 font-semibold">
                {isSinavlar ? "Sınav Yönetimi" : isInceleme ? "AI İnceleme Kuyruğu" : "Genel Bakış"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3.5">
            <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Motor 1 Aktif</span>
            </div>
            <Link
              href="/ogretmen/sinavlar?yukle=1"
              className="hidden sm:inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-xs hover:bg-indigo-700 transition-colors cursor-pointer"
            >
              <span>+ Yeni Kâğıt Yükle</span>
            </Link>
          </div>
        </header>

        {/* Dynamic Centered Page Container */}
        <main className="flex-1 px-4 sm:px-6 lg:px-10 py-8 max-w-6xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
