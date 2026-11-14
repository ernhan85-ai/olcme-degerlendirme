"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { ERROR_CATEGORY_TR, EXAM_STATUS_TR, JOB_STATUS_TR, flagLabel, num, trDate } from "@/lib/labels";
import type { ErrorCategory, ExamDetail, ItemAnalysis, JobStatus, Lookups, OutcomeReport, QuestionIn, ResponseAnalysis, Submission } from "@/lib/types";
import { Badge, Button, Card, Confirm, EmptyState, ErrorState, Loading, MockBadge, Modal, Tabs } from "@/components/ui";
import { UploadModal } from "@/components/UploadModal";
import { QuestionEditor } from "@/components/QuestionEditor";

type Tab = "papers" | "questions" | "items" | "outcomes";
const jobTone: Record<JobStatus, "neutral" | "info" | "warn" | "ok" | "bad"> = {
  uploaded: "neutral", queued: "neutral", processing: "info", requires_review: "warn", completed: "ok", failed: "bad",
};

function ExamPage() {
  const { id } = useParams<{ id: string }>();
  const sp = useSearchParams();
  const [exam, setExam] = useState<ExamDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("papers");
  const [uploadOpen, setUploadOpen] = useState(sp.get("yukle") === "1");

  const load = useCallback(() => {
    api<ExamDetail>(`/exams/${id}`).then((e) => { setExam(e); if (e.status !== "published") setTab((t) => (t === "papers" ? "questions" : t)); })
      .catch((e) => setErr(e.message));
  }, [id]);
  useEffect(load, [load]);

  if (err) return <ErrorState message={err} onRetry={load} />;
  if (!exam) return <Loading />;
  const published = exam.status === "published";

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <Link href="/ogretmen/sinavlar" className="text-sm font-semibold text-indigo-600 hover:text-indigo-800 transition-colors inline-flex items-center gap-1.5 mb-3">
          <span>←</span> Sınavlar Listesine Dön
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-5 pb-4 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg px-2.5 py-1">
                {exam.subject_name} • {exam.grade_level}. Sınıf
              </span>
              <Badge tone={published ? "ok" : "warn"}>{EXAM_STATUS_TR[exam.status]}</Badge>
            </div>
            <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-slate-900 leading-tight">
              {exam.title}
            </h1>
            <p className="mt-2 text-sm sm:text-base text-slate-500 font-medium">
              Sınav Tarihi: <span className="text-slate-800 font-semibold">{trDate(exam.exam_date)}</span> · Toplam <span className="text-slate-800 font-semibold">{exam.question_count} soru</span>
            </p>
          </div>
          <Button
            variant="hero"
            onClick={() => setUploadOpen(true)}
            disabled={!published}
            className="py-3 px-5 text-sm shadow-sm"
            title={published ? undefined : "Önce cevap anahtarını doğrulayıp sınavı yayımlayın"}
          >
            <span className="text-base font-bold">+</span> Yeni Öğrenci Kâğıdı Yükle
          </Button>
        </div>
      </div>

      <div>
        <Tabs
          value={tab}
          onChange={setTab}
          items={[
            { id: "papers", label: "Öğrenci Kâğıtları", count: exam.submission_count },
            { id: "questions", label: "Sorular ve Cevap Anahtarı", count: exam.question_count },
            { id: "items", label: "Madde Analizi (Psikometri)" },
            { id: "outcomes", label: "MEB Kazanım Raporu" },
          ]}
        />
        <div className="mt-6">
          {tab === "papers" && <Papers examId={id} published={published} onOpenUpload={() => setUploadOpen(true)} />}
          {tab === "questions" && <Questions exam={exam} onChange={setExam} />}
          {tab === "items" && <Items examId={id} exam={exam} />}
          {tab === "outcomes" && <Outcomes examId={id} />}
        </div>
      </div>
      <UploadModal examId={id} open={uploadOpen} onClose={() => setUploadOpen(false)} onDone={() => { load(); window.dispatchEvent(new Event("ldna:refresh")); }} />
    </div>
  );
}

// ---------------------------------------------------------------- papers
function Papers({ examId, published, onOpenUpload }: { examId: string; published: boolean; onOpenUpload: () => void }) {
  const [subs, setSubs] = useState<Submission[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [detail, setDetail] = useState<Submission | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(() => {
    api<Submission[]>(`/exams/${examId}/submissions`).then((s) => {
      setSubs(s);
      setErr(null);
      if (timer.current) clearTimeout(timer.current);
      if (s.some((x) => x.job && ["uploaded", "queued", "processing"].includes(x.job.status))) timer.current = setTimeout(load, 3000);
    }).catch((e) => setErr(e.message));
  }, [examId]);

  useEffect(() => {
    load();
    const h = () => load();
    window.addEventListener("ldna:refresh", h);
    return () => { window.removeEventListener("ldna:refresh", h); if (timer.current) clearTimeout(timer.current); };
  }, [load]);

  async function retry(id: string) {
    try { await api(`/submissions/${id}/retry`, { method: "POST" }); load(); } catch (e) { setErr((e as Error).message); }
  }

  if (err) return <ErrorState message={err} onRetry={load} />;
  if (!subs) return <Loading />;
  if (!subs.length) return (
    <EmptyState title="Henüz öğrenci kâğıdı yüklenmedi"
      hint={published ? "Taranmış kitapçıkları veya cevap kâğıtlarını yükleyin; sistem çözüm adımlarını analiz eder." : "Kâğıt yüklemek için önce sınavı yayımlayın."}
      action={published ? <Button variant="hero" onClick={onOpenUpload}>Yeni Öğrenci Yükle</Button> : undefined} />
  );

  return (
    <>
      <Card className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
            <tr><th className="px-5 py-3">Öğrenci</th><th>Durum</th><th>Puan</th><th>İnceleme</th><th>Dosya</th><th className="px-5 text-right">İşlem</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {subs.map((s) => (
              <tr key={s.id} className="hover:bg-paper/60">
                <td className="px-5 py-3"><span className="font-medium">{s.student.full_name}</span> <span className="text-muted">#{s.student.student_number}</span></td>
                <td>
                  {s.job && <Badge tone={jobTone[s.job.status]}>{JOB_STATUS_TR[s.job.status]}</Badge>}
                  {s.job?.provider_is_mock && <span className="ml-1"><MockBadge /></span>}
                  {s.job?.status === "failed" && s.job.error_message && <p className="mt-1 max-w-xs text-xs text-bad">{s.job.error_message}</p>}
                </td>
                <td className="tabular-nums">{s.total_score !== null ? `${num(s.total_score, 0)} / ${num(s.max_score, 0)}` : "—"}</td>
                <td>{s.needs_review_count > 0 ? <Badge tone="warn">{s.needs_review_count} soru</Badge> : <span className="text-muted">—</span>}</td>
                <td className="text-muted">{s.files.length}</td>
                <td className="px-5 text-right whitespace-nowrap">
                  {s.job && ["failed", "requires_review"].includes(s.job.status) && <Button variant="ghost" onClick={() => retry(s.id)}>Yeniden işle</Button>}
                  <Button variant="secondary" onClick={() => setDetail(s)}>Analizi aç</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {detail && <SubmissionDrawer sub={detail} onClose={() => setDetail(null)} />}
    </>
  );
}

function SubmissionDrawer({ sub, onClose }: { sub: Submission; onClose: () => void }) {
  const [rs, setRs] = useState<ResponseAnalysis[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api<ResponseAnalysis[]>(`/submissions/${sub.id}/responses`).then(setRs).catch((e) => setErr(e.message)); }, [sub.id]);
  return (
    <Modal open onClose={onClose} title={`${sub.student.full_name} — soru bazında analiz`} wide>
      {sub.job && (
        <details className="mb-4 text-xs text-muted">
          <summary className="cursor-pointer">İşlem geçmişi ({sub.job.attempts} deneme)</summary>
          <ul className="mt-2 space-y-1">{sub.job.log.map((l, i) => <li key={i}>{new Date(l.at).toLocaleString("tr-TR")} · {JOB_STATUS_TR[l.status]} {l.note && `· ${l.note}`}</li>)}</ul>
        </details>
      )}
      {err ? <ErrorState message={err} /> : !rs ? <Loading /> : rs.length === 0 ? <EmptyState title="Henüz cevap çıkarılmadı" /> : (
        <ul className="divide-y divide-line">
          {rs.map((r) => {
            const prim = r.hypotheses.find((h) => h.is_primary);
            return (
              <li key={r.id} className="flex items-center justify-between gap-4 py-3">
                <div className="min-w-0">
                  <p className="font-medium">{r.question.position}. soru <span className="ml-2 font-mono text-sm text-muted">{r.final_answer ?? "—"}</span></p>
                  <p className="truncate text-sm text-muted">{prim ? ERROR_CATEGORY_TR[prim.category] : r.is_correct ? "Doğru" : r.review_reason ?? ""}</p>
                </div>
                <div className="flex items-center gap-3">
                  {r.is_correct === true && <Badge tone="ok">Doğru</Badge>}
                  {r.is_correct === false && <Badge tone="bad">Yanlış</Badge>}
                  {r.is_correct === null && <Badge>Belirsiz</Badge>}
                  {r.needs_review && <Badge tone="warn">İnceleme</Badge>}
                  <Link href={`/ogretmen/analiz/${r.id}`}><Button>Aç →</Button></Link>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Modal>
  );
}

// ---------------------------------------------------------------- questions
function Questions({ exam, onChange }: { exam: ExamDetail; onChange: (e: ExamDetail) => void }) {
  const editable = exam.status !== "published" && exam.status !== "archived";
  const [lk, setLk] = useState<Lookups | null>(null);
  const [draft, setDraft] = useState<QuestionIn[]>(() => exam.questions.map((q) => ({
    position: q.position, stem_text: q.stem_text, answer_type: q.answer_type, options: q.options, points: q.points,
    correct_answer: q.correct_answer ?? "", reference_steps: q.reference_steps, outcome_ids: q.outcome_ids,
  })));
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [confirmPublish, setConfirmPublish] = useState(false);
  const csvRef = useRef<HTMLInputElement>(null);
  const pdfRef = useRef<HTMLInputElement>(null);

  useEffect(() => { api<Lookups>("/meta/lookups").then(setLk).catch(() => undefined); }, []);
  const outcomes = lk?.outcomes.filter((o) => o.grade_level === exam.grade_level && o.subject_id === exam.subject_id) ?? [];

  async function run(label: string, fn: () => Promise<ExamDetail>) {
    setBusy(label); setErr(null);
    try {
      const e = await fn();
      onChange(e);
      setDraft(e.questions.map((q) => ({ position: q.position, stem_text: q.stem_text, answer_type: q.answer_type, options: q.options, points: q.points, correct_answer: q.correct_answer ?? "", reference_steps: q.reference_steps, outcome_ids: q.outcome_ids })));
    } catch (e) { setErr((e as Error).message); } finally { setBusy(null); }
  }
  const upload = (path: string, f: File) => { const fd = new FormData(); fd.append("file", f, f.name); return api<ExamDetail>(path, { method: "POST", body: fd }); };

  return (
    <div className="flex flex-col gap-6">
      {exam.publish_blockers.length > 0 && editable && (
        <Card className="border-warn/40 bg-warn-soft p-5">
          <p className="font-medium text-warn">Yayımlamadan önce tamamlanması gerekenler</p>
          <ul className="mt-2 list-disc pl-5 text-sm text-ink-soft">{exam.publish_blockers.map((b, i) => <li key={i}>{b}</li>)}</ul>
        </Card>
      )}
      {editable && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => pdfRef.current?.click()} loading={busy === "pdf"}>{exam.has_booklet ? "Kitapçığı değiştir (PDF)" : "Sınav kitapçığı yükle (PDF)"}</Button>
          <Button onClick={() => csvRef.current?.click()} loading={busy === "csv"}>CSV'den soru içe aktar</Button>
          <Button onClick={() => run("save", () => api<ExamDetail>(`/exams/${exam.id}/questions`, { method: "PUT", body: JSON.stringify(draft) }))} loading={busy === "save"}>Soruları kaydet</Button>
          <Button onClick={() => run("validate", () => api<ExamDetail>(`/exams/${exam.id}/validate-keys`, { method: "POST" }))} loading={busy === "validate"}>Anahtarı ve kazanımları doğruladım</Button>
          <Button variant="primary" onClick={() => setConfirmPublish(true)}>Sınavı yayımla</Button>
          <input ref={pdfRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) run("pdf", () => upload(`/exams/${exam.id}/booklet?kind=booklet`, f)); e.target.value = ""; }} />
          <input ref={csvRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) run("csv", () => upload(`/exams/${exam.id}/questions/import-csv`, f)); e.target.value = ""; }} />
        </div>
      )}
      {err && <ErrorState message={err} />}
      {editable ? <QuestionEditor questions={draft} onChange={setDraft} outcomes={outcomes} /> : (
        <Card className="divide-y divide-line">
          {exam.questions.map((q) => (
            <div key={q.exam_question_id} className="grid gap-2 p-5 md:grid-cols-[60px_1fr_220px]">
              <p className="font-display text-2xl text-muted">{q.position}</p>
              <div>
                <p>{q.stem_text}</p>
                {q.reference_steps.length > 0 && <p className="mt-2 font-mono text-xs text-muted">{q.reference_steps.join("  →  ")}</p>}
              </div>
              <div className="text-sm">
                <p>Anahtar: <span className="font-mono font-medium">{q.correct_answer}</span></p>
                <p className="text-muted">{q.points} puan · {q.outcome_ids.map((oid) => lk?.outcomes.find((o) => o.id === oid)?.code).filter(Boolean).join(", ")}</p>
              </div>
            </div>
          ))}
        </Card>
      )}
      <Confirm open={confirmPublish} onClose={() => setConfirmPublish(false)} busy={busy === "publish"}
        title="Sınav yayımlansın mı?" confirmLabel="Yayımla"
        body="Yayımlandıktan sonra sorular ve cevap anahtarı kilitlenir; öğrenci kâğıtları yüklenebilir hâle gelir."
        onConfirm={() => { setConfirmPublish(false); run("publish", () => api<ExamDetail>(`/exams/${exam.id}/publish`, { method: "POST" })); }} />
    </div>
  );
}

// ---------------------------------------------------------------- item analysis
function Items({ examId, exam }: { examId: string; exam: ExamDetail }) {
  const [d, setD] = useState<ItemAnalysis | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api<ItemAnalysis>(`/exams/${examId}/item-analysis`).then(setD).catch((e) => setErr(e.message)); }, [examId]);
  if (err) return <ErrorState message={err} />;
  if (!d) return <Loading />;
  if (d.n_students === 0) return <EmptyState title="Madde analizi için veri yok" hint="Öğrenci kâğıtları işlendikçe madde istatistikleri burada oluşur." />;
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Kpi label="Öğrenci" value={String(d.n_students)} />
        <Kpi label="Ortalama başarı" value={d.mean_pct !== null ? `%${num(d.mean_pct, 1)}` : "—"} />
        <Kpi label="Standart sapma" value={d.sd_pct !== null ? num(d.sd_pct, 1) : "—"} />
        <Kpi label={`Güvenirlik (${d.reliability_method})`} value={num(d.reliability)} />
        <Kpi label="Ölçme hatası (SEM)" value={d.sem_pct !== null ? `±${num(d.sem_pct, 1)}` : "—"} />
      </div>
      {d.warnings.map((w, i) => <p key={i} className="rounded-lg bg-warn-soft px-4 py-2 text-sm text-warn">{w}</p>)}
      <Card className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
            <tr><th className="px-5 py-3">Soru</th><th>Güçlük (p)</th><th>Ayırt edicilik (r)</th><th>Alt-üst (D)</th><th>En sık hata türü</th><th className="pr-5">Uyarılar</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {d.items.map((it) => {
              const top = Object.entries(it.error_categories).sort((a, b) => b[1] - a[1])[0];
              return (
                <tr key={it.exam_question_id}>
                  <td className="px-5 py-3 font-medium">{it.position}. <span className="font-normal text-muted">{exam.questions.find((q) => q.exam_question_id === it.exam_question_id)?.stem_text.slice(0, 40)}</span></td>
                  <td><Bar v={it.difficulty_p} /></td>
                  <td className="tabular-nums">{num(it.discrimination_rpbis)}</td>
                  <td className="tabular-nums">{num(it.discrimination_d)}</td>
                  <td>{top ? <span>{ERROR_CATEGORY_TR[top[0] as ErrorCategory]} <span className="text-muted">({top[1]})</span></span> : "—"}</td>
                  <td className="pr-5"><div className="flex flex-wrap gap-1">{it.flags.map((f) => <Badge key={f} tone={f.startsWith("negatif") ? "bad" : "warn"}>{flagLabel(f)}</Badge>)}</div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
      <p className="text-xs text-muted">{d.note}</p>
    </div>
  );
}

function Bar({ v }: { v: number | null }) {
  if (v === null) return <>—</>;
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-20 overflow-hidden rounded-full bg-line"><div className="h-full bg-accent" style={{ width: `${v * 100}%` }} /></div>
      <span className="tabular-nums">{num(v)}</span>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return <Card className="p-4"><p className="text-xs text-muted">{label}</p><p className="mt-1 font-display text-3xl tabular-nums">{value}</p></Card>;
}

// ---------------------------------------------------------------- outcome report
function Outcomes({ examId }: { examId: string }) {
  const [d, setD] = useState<OutcomeReport | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api<OutcomeReport>(`/exams/${examId}/outcome-report`).then(setD).catch((e) => setErr(e.message)); }, [examId]);
  if (err) return <ErrorState message={err} />;
  if (!d) return <Loading />;
  if (!d.rows.length) return <EmptyState title="Kazanım eşleştirmesi yok" />;
  return (
    <div className="flex flex-col gap-4">
      {d.rows.map((r) => {
        const v = r.class_observed_pct;
        const tone = v === null ? "bg-line" : v >= 70 ? "bg-ok" : v >= 50 ? "bg-warn" : "bg-bad";
        return (
          <Card key={r.outcome_id} className="p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <div className="min-w-0">
                <p className="font-mono text-xs text-muted">{r.code}</p>
                <p className="font-medium">{r.description}</p>
              </div>
              <p className="font-display text-3xl tabular-nums">{v !== null ? `%${num(v, 0)}` : "—"}</p>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-line"><div className={`h-full ${tone}`} style={{ width: `${v ?? 0}%` }} /></div>
            <p className="mt-3 text-sm text-muted">
              {r.n_items} soru · %50 altında {r.students_below_50} öğrenci
              {r.top_error_category && <> · En sık hata türü: <span className="text-ink">{ERROR_CATEGORY_TR[r.top_error_category]}</span></>}
            </p>
          </Card>
        );
      })}
      <p className="text-xs text-muted">{d.note}</p>
    </div>
  );
}

export default function Page() {
  return <Suspense fallback={<Loading />}><ExamPage /></Suspense>;
}
