"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { ExamDetail, Lookups, QuestionIn } from "@/lib/types";
import { Button, Card, ErrorState, Field, Loading, inputCls } from "@/components/ui";
import { QuestionEditor, emptyQuestion } from "@/components/QuestionEditor";

export default function NewExamPage() {
  const router = useRouter();
  const [lk, setLk] = useState<Lookups | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ title: "", subject_id: "", grade_level: 0, class_ids: [] as string[], exam_date: new Date().toISOString().slice(0, 10) });
  const [questions, setQuestions] = useState<QuestionIn[]>([emptyQuestion(1)]);

  useEffect(() => { api<Lookups>("/meta/lookups").then(setLk).catch((e) => setErr(e.message)); }, []);

  const grades = useMemo(() => [...new Set(lk?.classes.map((c) => c.grade_level) ?? [])].sort((a, b) => a - b), [lk]);
  const classes = lk?.classes.filter((c) => c.grade_level === form.grade_level) ?? [];
  const outcomes = lk?.outcomes.filter((o) => o.grade_level === form.grade_level && (!form.subject_id || o.subject_id === form.subject_id)) ?? [];

  async function save() {
    setErr(null);
    setBusy(true);
    try {
      const qs = questions.filter((q) => q.stem_text.trim() && q.correct_answer.trim());
      const exam = await api<ExamDetail>("/exams", { method: "POST", body: JSON.stringify({ ...form, questions: qs }) });
      router.push(`/ogretmen/sinavlar/${exam.id}`);
    } catch (e) {
      setErr((e as Error).message);
      setBusy(false);
    }
  }

  if (!lk && !err) return <Loading />;
  const valid = form.title.length >= 2 && form.subject_id && form.grade_level && form.class_ids.length;

  return (
    <div className="mx-auto max-w-4xl">
      <p className="text-sm text-muted">Sınav Yönetimi</p>
      <h1 className="font-display text-4xl">Yeni sınav</h1>

      <Card className="mt-8 p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Sınav adı"><input className={inputCls} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="7. Sınıf Matematik – 1. Yazılı" /></Field>
          <Field label="Sınav tarihi"><input className={inputCls} type="date" value={form.exam_date} onChange={(e) => setForm({ ...form, exam_date: e.target.value })} /></Field>
          <Field label="Ders">
            <select className={inputCls} value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value })}>
              <option value="">Seçin</option>
              {lk?.subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="Sınıf düzeyi">
            <select className={inputCls} value={form.grade_level || ""} onChange={(e) => setForm({ ...form, grade_level: Number(e.target.value), class_ids: [] })}>
              <option value="">Seçin</option>
              {grades.map((g) => <option key={g} value={g}>{g}. sınıf</option>)}
            </select>
          </Field>
        </div>
        {form.grade_level > 0 && (
          <div className="mt-4">
            <Field label="Şubeler">
              <div className="flex flex-wrap gap-2">
                {classes.map((c) => {
                  const on = form.class_ids.includes(c.id);
                  return (
                    <button type="button" key={c.id} onClick={() => setForm({ ...form, class_ids: on ? form.class_ids.filter((x) => x !== c.id) : [...form.class_ids, c.id] })}
                      className={`rounded-lg border px-4 py-1.5 text-sm ${on ? "border-accent bg-accent-soft text-accent" : "border-line"}`}>{c.name}</button>
                  );
                })}
              </div>
            </Field>
          </div>
        )}
      </Card>

      <h2 className="mt-10 mb-1 font-display text-2xl">Sorular, cevap anahtarı ve kazanımlar</h2>
      <p className="mb-4 text-sm text-muted">
        Soruları burada girebilir ya da sınavı kaydettikten sonra CSV ile içe aktarabilirsiniz. Kitapçıktan otomatik soru çıkarımı,
        gerçek görüntü işleme sağlayıcısı yapılandırıldığında etkinleşecektir.
      </p>
      <QuestionEditor questions={questions} onChange={setQuestions} outcomes={outcomes} />

      {err && <div className="mt-6"><ErrorState message={err} /></div>}
      <div className="sticky bottom-0 mt-8 flex justify-end gap-3 border-t border-line bg-paper/90 py-4 backdrop-blur">
        <Button onClick={() => router.back()}>Vazgeç</Button>
        <Button variant="primary" onClick={save} loading={busy} disabled={!valid}>Sınavı kaydet</Button>
      </div>
    </div>
  );
}
