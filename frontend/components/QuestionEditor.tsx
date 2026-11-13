"use client";

import { ANSWER_TYPE_TR } from "@/lib/labels";
import type { AnswerType, OutcomeOut, QuestionIn } from "@/lib/types";
import { Button, Card, Field, inputCls } from "./ui";

export function emptyQuestion(position: number): QuestionIn {
  return { position, stem_text: "", answer_type: "equation", points: 10, correct_answer: "", reference_steps: [], outcome_ids: [], options: null };
}

function optionsToText(o: QuestionIn["options"]): string {
  if (!o) return "";
  return Object.entries(o).map(([k, v]) => `${k}=${typeof v === "object" && v ? (v as { text?: string }).text ?? "" : String(v)}`).join("\n");
}

function textToOptions(t: string): Record<string, string> | null {
  const entries = t.split("\n").map((l) => l.split("=")).filter((p) => p.length >= 2 && p[0].trim());
  return entries.length ? Object.fromEntries(entries.map(([k, ...v]) => [k.trim().toUpperCase(), v.join("=").trim()])) : null;
}

export function QuestionEditor({ questions, onChange, outcomes }: {
  questions: QuestionIn[]; onChange: (q: QuestionIn[]) => void; outcomes: OutcomeOut[];
}) {
  const update = (i: number, patch: Partial<QuestionIn>) => onChange(questions.map((q, j) => (j === i ? { ...q, ...patch } : q)));
  const remove = (i: number) => onChange(questions.filter((_, j) => j !== i).map((q, j) => ({ ...q, position: j + 1 })));

  return (
    <div className="flex flex-col gap-4">
      {questions.map((q, i) => (
        <Card key={i} className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-display text-lg">{q.position}. soru</h3>
            <Button variant="ghost" onClick={() => remove(i)} aria-label={`${q.position}. soruyu sil`}>Sil</Button>
          </div>
          <div className="grid gap-4 md:grid-cols-[1fr_200px_110px]">
            <Field label="Soru metni"><textarea className={inputCls} rows={2} value={q.stem_text} onChange={(e) => update(i, { stem_text: e.target.value })} /></Field>
            <Field label="Cevap türü">
              <select className={inputCls} value={q.answer_type} onChange={(e) => update(i, { answer_type: e.target.value as AnswerType })}>
                {Object.entries(ANSWER_TYPE_TR).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </Field>
            <Field label="Puan"><input className={inputCls} type="number" min={0.5} step={0.5} value={q.points} onChange={(e) => update(i, { points: Number(e.target.value) })} /></Field>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Field label="Doğru cevap" hint={q.answer_type === "multiple_choice" ? "Seçenek harfi (ör. C)" : "Ör. x=5, 5/6, 7a-6"}>
              <input className={`${inputCls} font-mono`} value={q.correct_answer} onChange={(e) => update(i, { correct_answer: e.target.value })} />
            </Field>
            {q.answer_type === "multiple_choice" ? (
              <Field label="Seçenekler" hint="Her satıra bir seçenek: A=x = 4">
                <textarea className={`${inputCls} font-mono`} rows={4} defaultValue={optionsToText(q.options)} onBlur={(e) => update(i, { options: textToOptions(e.target.value) })} />
              </Field>
            ) : (
              <Field label="Doğrulanmış referans çözüm adımları" hint="Her satıra bir adım. İlk satır sorunun matematiksel hali olmalı (ör. 3x+5=20). Adımlar SymPy ile kontrol edilir.">
                <textarea className={`${inputCls} font-mono`} rows={4} value={q.reference_steps.join("\n")}
                  onChange={(e) => update(i, { reference_steps: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean) })} />
              </Field>
            )}
          </div>
          <div className="mt-4">
            <Field label="Kazanım eşleştirmesi">
              <div className="flex flex-wrap gap-2">
                {outcomes.map((o) => {
                  const on = q.outcome_ids.includes(o.id);
                  return (
                    <button type="button" key={o.id} title={o.description}
                      onClick={() => update(i, { outcome_ids: on ? q.outcome_ids.filter((x) => x !== o.id) : [...q.outcome_ids, o.id] })}
                      className={`rounded-full border px-3 py-1 text-xs ${on ? "border-accent bg-accent-soft text-accent" : "border-line text-ink-soft hover:border-ink-soft"}`}>
                      {o.code}
                    </button>
                  );
                })}
                {outcomes.length === 0 && <span className="text-xs text-muted">Bu düzey/ders için tanımlı kazanım yok.</span>}
              </div>
            </Field>
          </div>
        </Card>
      ))}
      <Button onClick={() => onChange([...questions, emptyQuestion(questions.length + 1)])}>+ Soru ekle</Button>
    </div>
  );
}
