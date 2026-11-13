"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { EXAM_STATUS_TR, trDate } from "@/lib/labels";
import type { Exam, ExamStatus, Lookups } from "@/lib/types";
import { Badge, Button, Card, EmptyState, ErrorState, Loading, inputCls } from "@/components/ui";

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
    <div className="space-y-6">
      {/* Top CRM Title & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[11px] font-bold text-indigo-700 mb-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-600 animate-pulse" />
            ÖLÇME YÖNETİMİ • AKTİF DÖNEM
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
            Sınav & Değerlendirme Yönetimi
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Ölçme sınavlarınızı oluşturun, öğrenci çözüm kâğıtlarını yükleyin ve psikometrik analizleri takip edin.
          </p>
        </div>
        <Link href="/ogretmen/sinavlar/yeni">
          <Button variant="hero" className="py-2 px-4 shadow-sm text-xs">
            <span className="text-sm font-bold">+</span> Yeni Sınav Tanımla
          </Button>
        </Link>
      </div>

      {uploadMode && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/70 p-3.5 text-xs text-indigo-950 flex items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-xs">
              ↑
            </span>
            <div>
              <p className="font-bold text-slate-900">Öğrenci Kâğıdı Yükleme Modu</p>
              <p className="text-slate-600">Öğrenci kâğıdı yüklemek için lütfen aşağıdan yayımlanmış sınavı seçin.</p>
            </div>
          </div>
          <Link href="/ogretmen/sinavlar">
            <button className="text-indigo-700 font-semibold hover:underline text-xs cursor-pointer">
              Filtreyi Temizle
            </button>
          </Link>
        </div>
      )}

      {/* CRM Filter Bar */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-3 shadow-2xs">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
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

      {/* CRM Exam Cards */}
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
          <div className="grid gap-4 md:grid-cols-2">
            {exams.map((e) => (
              <Link
                key={e.id}
                href={`/ogretmen/sinavlar/${e.id}${uploadMode ? "?yukle=1" : ""}`}
                className="group block h-full"
              >
                <div className="h-full rounded-xl border border-slate-200/90 bg-white p-5 shadow-2xs hover:border-indigo-400 hover:shadow-xs transition-all duration-150 flex flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200/60 rounded px-2 py-0.5 mb-2">
                          <span>{e.subject_name}</span>
                          <span>•</span>
                          <span>{e.grade_level}. Sınıf</span>
                        </span>
                        <h2 className="font-bold text-base text-slate-900 group-hover:text-indigo-600 transition-colors leading-snug">
                          {e.title}
                        </h2>
                      </div>
                      <Badge tone={statusTone[e.status]}>{EXAM_STATUS_TR[e.status]}</Badge>
                    </div>

                    <p className="mt-2 text-xs text-slate-500">
                      Sınav Tarihi: {trDate(e.exam_date)}
                    </p>
                  </div>

                  <div className="mt-5 grid grid-cols-3 gap-2 pt-3 border-t border-slate-100">
                    <div className="rounded-lg bg-slate-50 p-2 text-center border border-slate-100">
                      <p className="text-base font-black text-slate-900 tabular-nums">
                        {e.question_count}
                      </p>
                      <p className="text-[10px] font-semibold uppercase text-slate-400">Soru</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-2 text-center border border-slate-100">
                      <p className="text-base font-black text-slate-900 tabular-nums">
                        {e.submission_count}
                      </p>
                      <p className="text-[10px] font-semibold uppercase text-slate-400">Öğrenci</p>
                    </div>
                    <div
                      className={`rounded-lg p-2 text-center border ${
                        e.pending_review_count > 0
                          ? "bg-amber-50/80 border-amber-200 text-amber-900"
                          : "bg-slate-50 border-slate-100 text-slate-900"
                      }`}
                    >
                      <p className="text-base font-black tabular-nums">
                        {e.pending_review_count}
                      </p>
                      <p className="text-[10px] font-semibold uppercase opacity-75">İnceleme</p>
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

export default function Page() {
  return (
    <Suspense fallback={<Loading label="Sınav paneli hazırlanıyor..." />}>
      <ExamList />
    </Suspense>
  );
}
