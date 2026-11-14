"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { EXAM_STATUS_TR, trDate } from "@/lib/labels";
import type { Exam, ExamStatus, Lookups } from "@/lib/types";
import { Badge, Button, EmptyState, ErrorState, Loading, inputCls } from "@/components/ui";

const statusTone: Record<ExamStatus, "neutral" | "ok" | "warn" | "info"> = {
  draft: "neutral",
  extracting: "info",
  in_review: "warn",
  published: "ok",
  archived: "neutral",
};

function ExamList() {
  const uploadMode = useSearchParams().get("yukle") === "1";
  const [exams, setExams] = useState<Exam[] | null>(null);
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [f, setF] = useState({ grade: "", subject: "", klass: "", status: uploadMode ? "published" : "" });

  const load = useCallback(() => {
    setErr(null);
    const q = new URLSearchParams();
    if (f.grade) q.set("grade_level", f.grade);
    if (f.subject) q.set("subject_id", f.subject);
    if (f.klass) q.set("class_id", f.klass);
    if (f.status) q.set("status", f.status);
    api<Exam[]>(`/exams?${q}`)
      .then(setExams)
      .catch((e) => setErr(e.message));
  }, [f]);

  useEffect(() => {
    api<Lookups>("/meta/lookups").then(setLookups).catch(() => undefined);
  }, []);
  useEffect(load, [load]);

  const grades = useMemo(
    () => [...new Set(lookups?.classes.map((c) => c.grade_level) ?? [])].sort((a, b) => a - b),
    [lookups],
  );

  return (
    <div className="space-y-8">
      {/* Top Banner / Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5 pb-2 border-b border-slate-200/80">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700 mb-2 shadow-2xs">
            <span className="h-2 w-2 rounded-full bg-indigo-600 animate-pulse" />
            ÖLÇME VE DEĞERLENDİRME PORTALI • 2026 GÜZ
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
            Sınav & Değerlendirme Yönetimi
          </h1>
          <p className="mt-2 text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl">
            Sınavlarınızı oluşturun, öğrenci el yazısı kâğıtlarını yükleyin, yapay zekâ bilişsel hata muhakemelerini onaylayın ve psikometrik madde analizlerini inceleyin.
          </p>
        </div>
        <Link href="/ogretmen/sinavlar/yeni" className="shrink-0">
          <Button variant="hero" className="py-3 px-5 text-sm shadow-sm">
            <span className="text-base font-bold">+</span> Yeni Sınav Tanımla
          </Button>
        </Link>
      </div>

      {uploadMode && (
        <div className="rounded-2xl border border-indigo-200 bg-indigo-50/80 p-5 text-sm text-indigo-950 flex items-center justify-between gap-4 shadow-xs">
          <div className="flex items-center gap-3.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white font-bold text-base shadow-xs">
              ↑
            </span>
            <div>
              <p className="font-bold text-base text-slate-900">Öğrenci Kâğıdı Yükleme Modu</p>
              <p className="text-slate-600 text-sm">Öğrenci el yazısı kâğıtlarını taramak ve işlemek için aşağıdaki yayımlanmış sınavı seçin.</p>
            </div>
          </div>
          <Link href="/ogretmen/sinavlar">
            <button className="text-indigo-700 font-bold hover:underline text-sm cursor-pointer whitespace-nowrap">
              Filtreyi Temizle ✕
            </button>
          </Link>
        </div>
      )}

      {/* Filter Bar */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-4 sm:p-5 shadow-xs">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          <select
            aria-label="Sınıf düzeyi"
            className={inputCls}
            value={f.grade}
            onChange={(e) => setF({ ...f, grade: e.target.value })}
          >
            <option value="">Tüm Sınıf Düzeyleri</option>
            {grades.map((g) => (
              <option key={g} value={g}>
                {g}. Sınıf
              </option>
            ))}
          </select>
          <select
            aria-label="Ders"
            className={inputCls}
            value={f.subject}
            onChange={(e) => setF({ ...f, subject: e.target.value })}
          >
            <option value="">Tüm Dersler</option>
            {lookups?.subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Şube"
            className={inputCls}
            value={f.klass}
            onChange={(e) => setF({ ...f, klass: e.target.value })}
          >
            <option value="">Tüm Şubeler</option>
            {lookups?.classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Durum"
            className={inputCls}
            value={f.status}
            onChange={(e) => setF({ ...f, status: e.target.value })}
          >
            <option value="">Tüm Durumlar</option>
            {Object.entries(EXAM_STATUS_TR).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Exam Cards Grid */}
      <div>
        {err ? (
          <ErrorState message={err} onRetry={load} />
        ) : exams === null ? (
          <Loading label="Sınavlar yükleniyor..." />
        ) : exams.length === 0 ? (
          <EmptyState
            title="Henüz bir sınav oluşturulmadı"
            hint="Sınav oluşturup soruları, referans çözümleri ve MEB kazanımlarını tanımlayabilirsiniz."
            action={
              <Link href="/ogretmen/sinavlar/yeni">
                <Button variant="hero">Yeni Sınav Tanımla</Button>
              </Link>
            }
          />
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {exams.map((e) => (
              <Link
                key={e.id}
                href={`/ogretmen/sinavlar/${e.id}${uploadMode ? "?yukle=1" : ""}`}
                className="group block h-full"
              >
                <div className="h-full rounded-2xl border border-slate-200/90 bg-white p-6 shadow-xs hover:border-indigo-400 hover:shadow-md transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <span className="inline-flex items-center gap-2 text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200/80 rounded-lg px-2.5 py-1 mb-3">
                          <span>{e.subject_name}</span>
                          <span>•</span>
                          <span>{e.grade_level}. Sınıf</span>
                        </span>
                        <h2 className="font-bold text-xl text-slate-900 group-hover:text-indigo-600 transition-colors leading-snug">
                          {e.title}
                        </h2>
                      </div>
                      <Badge tone={statusTone[e.status]}>{EXAM_STATUS_TR[e.status]}</Badge>
                    </div>

                    <p className="mt-3 text-sm text-slate-500 font-medium">
                      Sınav Tarihi: <span className="text-slate-800">{trDate(e.exam_date)}</span>
                    </p>
                  </div>

                  <div className="mt-6 grid grid-cols-3 gap-3 pt-4 border-t border-slate-100">
                    <div className="rounded-xl bg-slate-50 p-3 text-center border border-slate-200/60">
                      <p className="text-xl font-black text-slate-900 tabular-nums">
                        {e.question_count}
                      </p>
                      <p className="text-xs font-semibold uppercase text-slate-500 mt-0.5">Soru</p>
                    </div>
                    <div className="rounded-xl bg-slate-50 p-3 text-center border border-slate-200/60">
                      <p className="text-xl font-black text-slate-900 tabular-nums">
                        {e.submission_count}
                      </p>
                      <p className="text-xs font-semibold uppercase text-slate-500 mt-0.5">Öğrenci</p>
                    </div>
                    <div
                      className={`rounded-xl p-3 text-center border ${
                        e.pending_review_count > 0
                          ? "bg-amber-50/90 border-amber-300 text-amber-900 shadow-2xs"
                          : "bg-slate-50 border-slate-200/60 text-slate-900"
                      }`}
                    >
                      <p className="text-xl font-black tabular-nums">
                        {e.pending_review_count}
                      </p>
                      <p className="text-xs font-bold uppercase opacity-85 mt-0.5">İnceleme</p>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ExamsPage() {
  return (
    <Suspense fallback={<Loading label="Sınavlar yükleniyor..." />}>
      <ExamList />
    </Suspense>
  );
}
