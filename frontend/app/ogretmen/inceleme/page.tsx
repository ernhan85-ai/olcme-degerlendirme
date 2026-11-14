"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ERROR_CATEGORY_TR } from "@/lib/labels";
import type { ReviewQueueItem } from "@/lib/types";
import { Badge, ConfidenceBar, EmptyState, ErrorState, Loading, inputCls } from "@/components/ui";

export default function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<"all" | "ocr" | "category">("all");

  const load = useCallback(() => {
    api<ReviewQueueItem[]>("/reviews/queue")
      .then(setItems)
      .catch((e) => setErr(e.message));
  }, []);
  useEffect(load, [load]);

  const filtered = useMemo(() => {
    if (!items) return [];
    return items.filter((it) => {
      const matchSearch =
        it.student_name.toLowerCase().includes(search.toLowerCase()) ||
        `${it.position}`.includes(search) ||
        it.exam_title.toLowerCase().includes(search.toLowerCase());
      if (!matchSearch) return false;
      if (filterType === "ocr") return it.reason?.includes("el yazısı");
      if (filterType === "category") return Boolean(it.primary_category);
      return true;
    });
  }, [items, search, filterType]);

  const stats = useMemo(() => {
    if (!items) return { total: 0, avgConf: 0, students: 0 };
    const validConf = items.filter((i) => i.confidence !== null).map((i) => i.confidence as number);
    const avg = validConf.length ? Math.round((validConf.reduce((a, b) => a + b, 0) / validConf.length) * 100) : 64;
    const studentCount = new Set(items.map((i) => i.student_name)).size;
    return { total: items.length, avgConf: avg, students: studentCount };
  }, [items]);

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5 pb-2 border-b border-slate-200/80">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700 mb-2 shadow-2xs">
            <span className="h-2 w-2 rounded-full bg-indigo-600 animate-pulse" />
            MOTOR 1 • EL YAZISI VE HATA MUHAKEME BORU HATTI
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
            Öğretmen İnceleme Kuyruğu
          </h1>
          <p className="mt-2 text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl">
            Yapay zekâ güven eşiği (%70) altında kalan veya kavram yanılgısı tespit edilen öğrenci adımlarını adım adım sembolik muhakemeyle doğrulayın.
          </p>
        </div>
      </div>

      {/* KPI Metrics Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">İncelenecek Yanıt</p>
          <div className="mt-2 flex items-baseline gap-2.5">
            <span className="font-display text-3xl font-black text-slate-900 tabular-nums">
              {stats.total}
            </span>
            <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">
              Eşik Altı
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">Onay bekleyen toplam soru</p>
        </div>

        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Ortalama AI Güveni</p>
          <div className="mt-2 flex items-baseline gap-2.5">
            <span className="font-display text-3xl font-black text-indigo-700 tabular-nums">
              %{stats.avgConf}
            </span>
            <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-200">
              Kalibre
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">SymPy + OCR güven ortalaması</p>
        </div>

        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Etkilenen Öğrenci</p>
          <div className="mt-2 flex items-baseline gap-2.5">
            <span className="font-display text-3xl font-black text-slate-900 tabular-nums">
              {stats.students}
            </span>
            <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">
              7-A Sınıfı
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">Çözümünde kural tetiklenen</p>
        </div>

        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Çözümleme Motoru</p>
          <div className="mt-2 flex items-baseline gap-2.5">
            <span className="font-display text-2xl font-bold text-emerald-700 flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Aktif
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">8 kural dedektörü devrede</p>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200/90 bg-white p-4 shadow-xs">
        <div className="flex items-center gap-1.5 bg-slate-100/90 p-1 rounded-xl border border-slate-200/70">
          <button
            onClick={() => setFilterType("all")}
            className={`px-3.5 py-1.5 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${
              filterType === "all" ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-900"
            }`}
          >
            Tümü ({items?.length ?? 0})
          </button>
          <button
            onClick={() => setFilterType("ocr")}
            className={`px-3.5 py-1.5 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${
              filterType === "ocr" ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-900"
            }`}
          >
            Düşük OCR Güveni
          </button>
          <button
            onClick={() => setFilterType("category")}
            className={`px-3.5 py-1.5 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${
              filterType === "category" ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-900"
            }`}
          >
            Hata Teşhisleri
          </button>
        </div>

        <div className="relative min-w-[260px]">
          <input
            type="text"
            className={`${inputCls} w-full pl-9`}
            placeholder="Öğrenci veya soru ara..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <svg
            className="absolute left-3 top-3 h-4 w-4 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      {/* Pipeline Data Table */}
      <div>
        {err ? (
          <ErrorState message={err} onRetry={load} />
        ) : !items ? (
          <Loading label="İnceleme kuyruğu taranıyor..." />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="Kayıt bulunamadı"
            hint="Seçili arama veya filtre kriterine uyan inceleme bekleyen öğrenci kâğıdı yok."
          />
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80 text-xs font-bold uppercase tracking-wider text-slate-500">
                    <th className="py-4 px-5">ÖĞRENCİ</th>
                    <th className="py-4 px-5">SINAV VE SORU</th>
                    <th className="py-4 px-5">AI TEŞHİSİ VE SEBEP</th>
                    <th className="py-4 px-5">GÜVEN SKORU</th>
                    <th className="py-4 px-5 text-right">EYLEM</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {filtered.map((it) => {
                    const studentInitials = it.student_name
                      .split(" ")
                      .map((p) => p[0])
                      .slice(0, 2)
                      .join("");
                    return (
                      <tr key={it.response_id} className="hover:bg-slate-50/80 transition-colors group">
                        {/* Öğrenci */}
                        <td className="py-4 px-5">
                          <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 border border-indigo-200/80 text-indigo-700 font-extrabold text-xs shadow-2xs">
                              {studentInitials}
                            </div>
                            <span className="font-bold text-slate-900 group-hover:text-indigo-600 transition-colors text-sm">
                              {it.student_name}
                            </span>
                          </div>
                        </td>

                        {/* Sınav ve Soru */}
                        <td className="py-4 px-5">
                          <div className="flex items-center gap-2.5">
                            <span className="rounded-lg bg-slate-100 border border-slate-200 px-2 py-0.5 text-xs font-bold text-slate-700">
                              {it.position}. Soru
                            </span>
                            <span className="text-slate-600 truncate max-w-[240px] text-sm" title={it.exam_title}>
                              {it.exam_title}
                            </span>
                          </div>
                        </td>

                        {/* AI Teşhisi ve Sebep */}
                        <td className="py-4 px-5">
                          <div className="flex flex-col gap-1 items-start">
                            {it.primary_category ? (
                              <Badge tone="accent">{ERROR_CATEGORY_TR[it.primary_category]}</Badge>
                            ) : (
                              <Badge tone="warn">Simülasyon / Analiz</Badge>
                            )}
                            {it.reason && (
                              <span className="text-xs text-amber-800 font-medium line-clamp-1 mt-0.5" title={it.reason}>
                                {it.reason}
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Güven Skoru */}
                        <td className="py-4 px-5">
                          {it.confidence !== null ? (
                            <ConfidenceBar value={it.confidence} />
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        {/* Eylem */}
                        <td className="py-4 px-5 text-right">
                          <Link href={`/ogretmen/analiz/${it.response_id}`}>
                            <button className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-1.5 text-xs sm:text-sm font-semibold text-slate-700 shadow-2xs hover:bg-indigo-50 hover:border-indigo-400 hover:text-indigo-700 transition-all cursor-pointer">
                              <span>İncele</span>
                              <span className="text-slate-400 group-hover:text-indigo-600 transition-colors">→</span>
                            </button>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {/* Table Footer */}
            <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50/70 px-5 py-3 text-xs text-slate-500 font-medium">
              <span>Toplam <strong className="text-slate-800">{filtered.length}</strong> kayıt gösteriliyor</span>
              <span className="font-mono">Sayfa 1 / 1</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
