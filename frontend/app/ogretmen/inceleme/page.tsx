"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ERROR_CATEGORY_TR } from "@/lib/labels";
import type { ReviewQueueItem } from "@/lib/types";
import { Badge, Button, Card, ConfidenceBar, EmptyState, ErrorState, Loading, inputCls } from "@/components/ui";

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
    <div className="space-y-6">
      {/* Top CRM Title & Subtitle */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[11px] font-bold text-indigo-700 mb-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-600 animate-pulse" />
            MOTOR 1 • EL YAZISI VE HATA MUHAKEME BORU HATTI
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
            Öğretmen İnceleme Kuyruğu
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Yapay zekâ güven eşiği (%70) altında kalan veya kavram yanılgısı tespit edilen öğrenci adımları.
          </p>
        </div>
      </div>

      {/* CRM KPI Metrics Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-2xs">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">İncelenecek Yanıt</p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-display text-2xl font-black text-slate-900 tabular-nums">
              {stats.total}
            </span>
            <span className="text-[11px] font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200/60">
              Eşik Altı
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Onay bekleyen toplam soru</p>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-2xs">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Ortalama AI Güveni</p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-display text-2xl font-black text-indigo-700 tabular-nums">
              %{stats.avgConf}
            </span>
            <span className="text-[11px] font-semibold text-indigo-600 bg-indigo-50 px-1.5 py-0.2 rounded border border-indigo-200/60">
              Kalibre
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">SymPy + OCR güven ortalaması</p>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-2xs">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Etkilenen Öğrenci</p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-display text-2xl font-black text-slate-900 tabular-nums">
              {stats.students}
            </span>
            <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded">
              7-A Sınıfı
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Çözümünde kural tetiklenen</p>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-2xs">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Çözümleme Motoru</p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-display text-xl font-bold text-emerald-700 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500" /> Aktif
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">8 kural dedektörü devrede</p>
        </div>
      </div>

      {/* CRM Filter & Search Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-slate-200/80 bg-white p-2.5 shadow-2xs">
        <div className="flex items-center gap-1 bg-slate-100/80 p-0.5 rounded-lg border border-slate-200/60">
          <button
            onClick={() => setFilterType("all")}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
              filterType === "all" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
            }`}
          >
            Tümü ({items?.length ?? 0})
          </button>
          <button
            onClick={() => setFilterType("ocr")}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
              filterType === "ocr" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
            }`}
          >
            Düşük OCR Güveni
          </button>
          <button
            onClick={() => setFilterType("category")}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
              filterType === "category" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
            }`}
          >
            Hata Teşhisleri
          </button>
        </div>

        <div className="relative min-w-[240px]">
          <input
            type="text"
            className={`${inputCls} w-full pl-8`}
            placeholder="Öğrenci veya soru ara..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <svg
            className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      {/* CRM Pipeline Data Table */}
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
          <div className="overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-2xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200/80 bg-slate-50/80 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    <th className="py-3 px-4">ÖĞRENCİ</th>
                    <th className="py-3 px-4">SINAV VE SORU</th>
                    <th className="py-3 px-4">AI TEŞHİSİ VE SEBEP</th>
                    <th className="py-3 px-4">GÜVEN SKORU</th>
                    <th className="py-3 px-4 text-right">EYLEM</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {filtered.map((it) => {
                    const studentInitials = it.student_name
                      .split(" ")
                      .map((p) => p[0])
                      .slice(0, 2)
                      .join("");
                    return (
                      <tr key={it.response_id} className="hover:bg-slate-50/70 transition-colors group">
                        {/* Öğrenci */}
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2.5">
                            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-indigo-50 border border-indigo-200/60 text-indigo-700 font-bold text-[11px]">
                              {studentInitials}
                            </div>
                            <span className="font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                              {it.student_name}
                            </span>
                          </div>
                        </td>

                        {/* Sınav ve Soru */}
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="rounded bg-slate-100 border border-slate-200/80 px-1.5 py-0.5 text-[11px] font-bold text-slate-700">
                              {it.position}. Soru
                            </span>
                            <span className="text-slate-500 truncate max-w-[220px]" title={it.exam_title}>
                              {it.exam_title}
                            </span>
                          </div>
                        </td>

                        {/* AI Teşhisi ve Sebep */}
                        <td className="py-3 px-4">
                          <div className="flex flex-col gap-1 items-start">
                            {it.primary_category ? (
                              <Badge tone="accent">{ERROR_CATEGORY_TR[it.primary_category]}</Badge>
                            ) : (
                              <Badge tone="warn">Simülasyon / Analiz</Badge>
                            )}
                            {it.reason && (
                              <span className="text-[11px] text-amber-700 font-medium line-clamp-1" title={it.reason}>
                                {it.reason}
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Güven Skoru */}
                        <td className="py-3 px-4">
                          {it.confidence !== null ? (
                            <ConfidenceBar value={it.confidence} />
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        {/* Eylem */}
                        <td className="py-3 px-4 text-right">
                          <Link href={`/ogretmen/analiz/${it.response_id}`}>
                            <button className="inline-flex items-center gap-1 rounded-lg border border-slate-200/80 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700 transition-all cursor-pointer">
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
            <div className="flex items-center justify-between border-t border-slate-200/80 bg-slate-50/50 px-4 py-2.5 text-[11px] text-slate-500">
              <span>Toplam {filtered.length} kayıt gösteriliyor</span>
              <span className="font-mono">Sayfa 1 / 1</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
