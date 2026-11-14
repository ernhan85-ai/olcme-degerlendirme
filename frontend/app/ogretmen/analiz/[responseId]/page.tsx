"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { ERROR_CATEGORY_TR, REVIEW_STATUS_TR, VERDICT_TR, num } from "@/lib/labels";
import type { ErrorCategory, Hypothesis, ResponseAnalysis, StepVerdict } from "@/lib/types";
import { Badge, Button, Card, ConfidenceBar, ErrorState, Field, Loading, MockBadge, cx, inputCls } from "@/components/ui";
import { type Box, DocumentViewer } from "@/components/DocumentViewer";

const UNREADABLE = "Öğrenci çözümü güvenilir biçimde analiz edilemedi. Öğretmen incelemesi gerekiyor.";
const verdictTone: Record<StepVerdict, string> = {
  valid: "border-l-ok", invalid: "border-l-bad bg-bad-soft/40", unverifiable: "border-l-warn", not_checked: "border-l-line opacity-60",
};
const verdictIcon: Record<StepVerdict, string> = { valid: "✓", invalid: "✕", unverifiable: "?", not_checked: "–" };

export default function AnalysisPage() {
  const { responseId } = useParams<{ responseId: string }>();
  const [r, setR] = useState<ResponseAnalysis | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [hl, setHl] = useState<string | null>(null);

  const load = useCallback(() => { api<ResponseAnalysis>(`/responses/${responseId}`).then(setR).catch((e) => setErr(e.message)); }, [responseId]);
  useEffect(load, [load]);

  if (err && !r) return <ErrorState message={err} onRetry={load} />;
  if (!r) return <Loading />;

  const boxes: Box[] = [
    ...r.steps.map((s): Box => ({ id: `step-${s.step_index}`, page: s.page, bbox: s.bbox, tone: s.verdict === "invalid" ? "invalid" : "step" })),
    { id: "answer", page: r.source_page, bbox: r.source_bbox, tone: "answer" },
    ...r.hypotheses.flatMap((h) => h.evidence.map((e): Box => ({ id: `ev-${e.id}`, page: e.page, bbox: e.bbox, tone: "evidence" }))),
  ];
  const unreadable = r.review_reason?.includes(UNREADABLE) || (!r.steps.length && r.final_answer === null);

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <div>
        <Link href={`/ogretmen/sinavlar/${r.exam_id}`} className="text-sm font-semibold text-indigo-600 hover:text-indigo-800 transition-colors inline-flex items-center gap-1.5 mb-2">
          <span>←</span> {r.exam_title} Sınavına Dön
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-slate-900 leading-tight">
            {r.student.full_name} · {r.question.position}. Soru Çözümü
          </h1>
          {r.provider_is_mock && <MockBadge />}
          {r.transcription_source === "teacher" && <Badge tone="info">Öğretmen transkripsiyonu</Badge>}
        </div>
        <p className="mt-2 max-w-4xl text-base text-slate-600 leading-relaxed font-medium bg-slate-50 p-3.5 rounded-xl border border-slate-200">
          <strong className="text-slate-900">Soru Metni:</strong> {r.question.stem_text}
        </p>
      </div>

      {unreadable && (
        <div role="alert" className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm font-medium text-amber-900 shadow-2xs">
          {UNREADABLE}
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)_minmax(0,1fr)]">
        {/* LEFT — original */}
        <Card className="p-4">
          <PanelTitle n="1" title="Öğrenci kâğıdı" />
          <DocumentViewer files={r.files} boxes={boxes} highlight={hl} initialPage={r.source_page} />
        </Card>

        {/* CENTER — extracted steps */}
        <Card className="p-4">
          <PanelTitle n="2" title="Çıkarılan çözüm adımları" />
          <StepsPanel r={r} onSaved={setR} onHover={setHl} />
        </Card>

        {/* RIGHT — AI analysis */}
        <Card className="p-4">
          <PanelTitle n="3" title="Yapay zekâ hata analizi" />
          <ResultSummary r={r} onSaved={setR} />
          {r.review_reason && !unreadable && <p className="mt-3 rounded-lg bg-warn-soft px-3 py-2 text-xs text-warn">{r.review_reason}</p>}
          <div className="mt-4 flex flex-col gap-4">
            {r.hypotheses.length === 0 && r.is_correct && <p className="text-sm text-muted">Cevap doğru; geçersiz adım tespit edilmedi.</p>}
            {r.hypotheses.map((h) => <HypothesisCard key={h.id} h={h} onSaved={setR} onHover={setHl} />)}
          </div>
          <div className="mt-6 rounded-xl border border-dashed border-line p-4 text-xs text-muted">
            <p className="font-medium text-ink-soft">Pedagojik müdahale önerileri</p>
            Müdahale önerileri Pedagojik Karar Motoru (Faz 4) devreye alındığında bu hata analizine göre burada listelenecek ve öğretmen onayına sunulacaktır.
          </div>
        </Card>
      </div>
    </div>
  );
}

function PanelTitle({ n, title }: { n: string; title: string }) {
  return (
    <p className="mb-4 flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-slate-700">
      <span className="grid h-6 w-6 place-items-center rounded-lg bg-indigo-600 text-xs font-black text-white shadow-2xs">
        {n}
      </span>
      {title}
    </p>
  );
}

// ---------------------------------------------------------------- steps
function StepsPanel({ r, onSaved, onHover }: { r: ResponseAnalysis; onSaved: (r: ResponseAnalysis) => void; onHover: (id: string | null) => void }) {
  const [edit, setEdit] = useState(false);
  const [text, setText] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function startEdit() {
    setText(r.steps.map((s) => `${s.is_crossed_out ? "~" : ""}${s.raw_text}`).join("\n"));
    setAnswer(r.final_answer ?? "");
    setEdit(true);
  }

  async function save() {
    setBusy(true); setErr(null);
    const prev = new Map(r.steps.map((s) => [s.step_index, s]));
    const steps = text.split("\n").map((l) => l.trim()).filter(Boolean).map((l, i) => {
      const crossed = l.startsWith("~");
      const old = prev.get(i);
      return { raw_text: crossed ? l.slice(1).trim() : l, is_crossed_out: crossed, page: old?.page ?? null, bbox: old?.bbox ?? null };
    });
    try {
      onSaved(await api<ResponseAnalysis>(`/responses/${r.id}/transcription`, { method: "PUT", body: JSON.stringify({ final_answer: answer.trim() || null, steps }) }));
      setEdit(false);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  if (edit) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-xs text-muted">Her satıra bir adım yazın. Üstü çizili adımları <code>~</code> ile başlatın. Kaydettiğinizde analiz yeniden çalışır; değişiklik denetim kaydına yazılır.</p>
        <textarea className={`${inputCls} font-mono`} rows={Math.max(6, text.split("\n").length + 1)} value={text} onChange={(e) => setText(e.target.value)} aria-label="Çözüm adımları" />
        <Field label="Öğrencinin cevabı"><input className={`${inputCls} font-mono`} value={answer} onChange={(e) => setAnswer(e.target.value)} /></Field>
        {err && <ErrorState message={err} />}
        <div className="flex justify-end gap-2"><Button onClick={() => setEdit(false)}>Vazgeç</Button><Button variant="primary" onClick={save} loading={busy}>Kaydet ve yeniden analiz et</Button></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {r.steps.length === 0 && <p className="rounded-lg bg-paper p-4 text-sm text-muted">Çözüm adımı bulunamadı. Kâğıtta işlem varsa “Düzelt” ile ekleyin — sistem eksik çözümü kendiliğinden tamamlamaz.</p>}
      {r.steps.map((s) => (
        <div key={s.id} onMouseEnter={() => onHover(`step-${s.step_index}`)} onMouseLeave={() => onHover(null)}
          className={cx("rounded-lg border border-line border-l-4 px-3 py-2", verdictTone[s.verdict])}>
          <div className="flex items-center justify-between gap-2">
            <span className={cx("font-mono text-[15px]", s.is_crossed_out && "line-through text-muted")}>{s.raw_text}</span>
            <span title={VERDICT_TR[s.verdict]} className="text-sm">{verdictIcon[s.verdict]}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 text-[11px] text-muted">
            <span>{s.step_index + 1}. adım</span>
            {s.verdict_detail && <span>{s.verdict_detail}</span>}
            {s.ocr_confidence !== null && !s.edited_by_teacher && (
              <span className={s.ocr_confidence < 0.6 ? "font-medium text-bad" : ""}>Okuma güveni %{Math.round(s.ocr_confidence * 100)}</span>
            )}
            {s.edited_by_teacher && <span className="text-info">öğretmen düzeltti</span>}
          </div>
        </div>
      ))}
      <div className="mt-2 rounded-lg bg-paper px-3 py-2 text-sm" onMouseEnter={() => onHover("answer")} onMouseLeave={() => onHover(null)}>
        <span className="text-muted">Cevap:</span> <span className="font-mono font-medium">{r.final_answer ?? "—"}</span>
        <span className="ml-3 text-muted">Anahtar:</span> <span className="font-mono">{r.question.correct_answer}</span>
      </div>
      <Button className="mt-2 self-start" onClick={startEdit}>Okumayı düzelt</Button>
    </div>
  );
}

// ---------------------------------------------------------------- result + score
function ResultSummary({ r, onSaved }: { r: ResponseAnalysis; onSaved: (r: ResponseAnalysis) => void }) {
  const [open, setOpen] = useState(false);
  const [score, setScore] = useState(String(r.score ?? ""));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  async function save() {
    setBusy(true); setErr(null);
    try { onSaved(await api(`/responses/${r.id}/score`, { method: "POST", body: JSON.stringify({ score: Number(score.replace(",", ".")) }) })); setOpen(false); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  return (
    <div className="rounded-xl bg-paper p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {r.is_correct === true && <Badge tone="ok">Doğru</Badge>}
          {r.is_correct === false && <Badge tone="bad">Yanlış</Badge>}
          {r.is_correct === null && <Badge>Otomatik belirlenemedi</Badge>}
          <span className="font-display text-2xl tabular-nums">{r.score !== null ? num(r.score, 1) : "—"}<span className="text-base text-muted"> / {r.question.points}</span></span>
        </div>
        <Button variant="ghost" onClick={() => setOpen(!open)}>Puanı değiştir</Button>
      </div>
      {open && (
        <div className="mt-3 flex items-end gap-2">
          <Field label={`Puan (0–${r.question.points})`}><input className={`${inputCls} w-28`} value={score} onChange={(e) => setScore(e.target.value)} inputMode="decimal" /></Field>
          <Button variant="primary" onClick={save} loading={busy}>Kaydet</Button>
        </div>
      )}
      {err && <div className="mt-2"><ErrorState message={err} /></div>}
    </div>
  );
}

// ---------------------------------------------------------------- hypothesis
function HypothesisCard({ h, onSaved, onHover }: { h: Hypothesis; onSaved: (r: ResponseAnalysis) => void; onHover: (id: string | null) => void }) {
  const [mode, setMode] = useState<"idle" | "modify">("idle");
  const [cat, setCat] = useState<ErrorCategory>(h.category);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function review(action: "approved" | "modified" | "rejected") {
    setBusy(action); setErr(null);
    try {
      onSaved(await api(`/hypotheses/${h.id}/review`, { method: "POST", body: JSON.stringify({ action, corrected_category: action === "modified" ? cat : null, note: note || null }) }));
      setMode("idle");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(null); }
  }

  const reviewed = ["approved", "modified", "rejected"].includes(h.review_status);

  return (
    <div className={cx("rounded-xl border p-4", h.is_primary ? "border-ink/30" : "border-line", h.review_status === "rejected" && "opacity-60")}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-[11px] uppercase tracking-wider text-muted">{h.is_primary ? "Birincil hipotez" : "Ek hipotez"}</p>
          <p className="font-display text-lg">{ERROR_CATEGORY_TR[h.category]}</p>
        </div>
        <Badge tone={h.review_status === "pending" ? "warn" : reviewed ? "info" : "neutral"}>{REVIEW_STATUS_TR[h.review_status]}</Badge>
      </div>
      <div className="mt-2"><ConfidenceBar value={h.calibrated_confidence} label={`Güven %${Math.round(h.calibrated_confidence * 100)}`} /></div>

      <dl className="mt-4 space-y-3 text-sm">
        <div><dt className="text-xs font-semibold text-ink-soft">Gözlenen (kâğıtta görülen)</dt><dd>{h.observed_error}</dd></div>
        <div><dt className="text-xs font-semibold text-ink-soft">Olası neden (yapay zekâ hipotezi)</dt><dd>{h.inferred_cause}</dd></div>
        <div>
          <dt className="text-xs font-semibold text-ink-soft">Kanıtlar</dt>
          <dd><ul className="mt-1 space-y-1">{h.evidence.map((e) => (
            <li key={e.id} onMouseEnter={() => onHover(e.bbox ? `ev-${e.id}` : e.step_index !== null ? `step-${e.step_index}` : null)} onMouseLeave={() => onHover(null)}
              className="cursor-default rounded-md bg-paper px-2 py-1 text-xs">
              {e.description} <span className="text-muted">· {e.verified_by === "sympy" ? "SymPy ile doğrulandı" : e.verified_by === "rule" ? "kural tabanlı" : e.verified_by === "ocr" ? "görüntü okuma" : "doğrulanmamış"}</span>
            </li>))}</ul></dd>
        </div>
        {h.alternative_explanations.length > 0 && (
          <div><dt className="text-xs font-semibold text-ink-soft">Alternatif açıklamalar</dt><dd><ul className="list-disc pl-5 text-ink-soft">{h.alternative_explanations.map((a, i) => <li key={i}>{a}</li>)}</ul></dd></div>
        )}
        {h.diagnostic_questions.length > 0 && (
          <div><dt className="text-xs font-semibold text-ink-soft">Önerilen tanılayıcı sorular</dt><dd><ul className="list-disc pl-5">{h.diagnostic_questions.map((a, i) => <li key={i}>{a}</li>)}</ul></dd></div>
        )}
        {h.llm_explanation && (
          <div className="rounded-lg border border-dashed border-line p-3">
            <dt className="flex items-center gap-2 text-xs font-semibold text-ink-soft">Doğrulanmamış yapay zekâ açıklaması {h.llm_explanation_is_mock && <MockBadge />}</dt>
            <dd className="mt-1 text-ink-soft">{h.llm_explanation}</dd>
          </div>
        )}
      </dl>

      {mode === "modify" && (
        <div className="mt-4 grid gap-2">
          <select className={inputCls} value={cat} onChange={(e) => setCat(e.target.value as ErrorCategory)} aria-label="Doğru hata kategorisi">
            {Object.entries(ERROR_CATEGORY_TR).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <textarea className={inputCls} rows={2} placeholder="Not (isteğe bağlı)" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
      )}
      {err && <div className="mt-3"><ErrorState message={err} /></div>}
      <div className="mt-4 flex flex-wrap gap-2">
        {mode === "modify" ? (
          <><Button onClick={() => setMode("idle")}>Vazgeç</Button><Button variant="primary" loading={busy === "modified"} onClick={() => review("modified")}>Düzeltmeyi kaydet</Button></>
        ) : (
          <>
            <Button variant="primary" loading={busy === "approved"} onClick={() => review("approved")}>Onayla</Button>
            <Button onClick={() => setMode("modify")}>Düzelt</Button>
            <Button variant="ghost" loading={busy === "rejected"} onClick={() => review("rejected")}>Reddet</Button>
          </>
        )}
      </div>
      <p className="mt-3 text-[10px] text-muted">Motor {h.engine_version} · {h.detector} · ham güven %{Math.round(h.raw_confidence * 100)}</p>
    </div>
  );
}
