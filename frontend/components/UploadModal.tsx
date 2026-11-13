"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Student, Submission, UploadResult } from "@/lib/types";
import { Button, ErrorState, Field, Modal, Tabs, inputCls } from "./ui";

const ACCEPT = "application/pdf,image/png,image/jpeg,image/tiff";
const MAX_MB = 40;

export function UploadModal({ examId, open, onClose, onDone }: {
  examId: string; open: boolean; onClose: () => void; onDone: () => void;
}) {
  const [mode, setMode] = useState<"single" | "bulk">("single");
  const [students, setStudents] = useState<Student[]>([]);
  const [studentId, setStudentId] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) api<Student[]>(`/exams/${examId}/students`).then(setStudents).catch((e) => setErr(e.message));
  }, [open, examId]);

  function reset() { setFiles([]); setStudentId(""); setErr(null); setResult(null); }

  function addFiles(list: FileList | null) {
    if (!list) return;
    const arr = Array.from(list);
    const tooBig = arr.find((f) => f.size > MAX_MB * 1024 * 1024);
    if (tooBig) { setErr(`'${tooBig.name}' ${MAX_MB} MB sınırını aşıyor.`); return; }
    setErr(null);
    setFiles((prev) => [...prev, ...arr]);
  }

  async function submit() {
    setBusy(true);
    setErr(null);
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f, f.name));
    try {
      if (mode === "single") {
        fd.append("student_id", studentId);
        const sub = await api<Submission>(`/exams/${examId}/submissions`, { method: "POST", body: fd });
        setResult({ created: [sub], errors: [] });
      } else {
        setResult(await api<UploadResult>(`/exams/${examId}/submissions/bulk`, { method: "POST", body: fd }));
      }
      setFiles([]);
      onDone();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const canSubmit = files.length > 0 && (mode === "bulk" || studentId);

  return (
    <Modal open={open} onClose={() => { reset(); onClose(); }} title="Yeni Öğrenci Yükle" wide>
      <Tabs value={mode} onChange={(m) => { setMode(m); reset(); }} items={[{ id: "single", label: "Tek öğrenci" }, { id: "bulk", label: "Toplu yükleme" }]} />
      <div className="mt-5 flex flex-col gap-5">
        {mode === "single" ? (
          <Field label="Öğrenci">
            <select className={inputCls} value={studentId} onChange={(e) => setStudentId(e.target.value)}>
              <option value="">Öğrenci seçin</option>
              {students.map((s) => <option key={s.id} value={s.id}>{s.student_number} — {s.full_name}</option>)}
            </select>
          </Field>
        ) : (
          <p className="rounded-lg bg-info-soft px-4 py-3 text-sm text-info">
            Dosya adları öğrenci numarasıyla başlamalıdır: <code className="font-mono">1024_sayfa1.jpg</code>, <code className="font-mono">1024_sayfa2.jpg</code>, <code className="font-mono">1031.pdf</code>.
            Aynı numaralı dosyalar tek kâğıt olarak birleştirilir; sayfa sırası dosya adına göre belirlenir.
          </p>
        )}

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); addFiles(e.dataTransfer.files); }}
          onClick={() => inputRef.current?.click()}
          className="cursor-pointer rounded-2xl border-2 border-dashed border-line bg-paper px-6 py-10 text-center hover:border-accent"
        >
          <p className="font-medium">Cevap kâğıdı, taranmış kitapçık veya fotoğrafları sürükleyin</p>
          <p className="mt-1 text-sm text-muted">PDF, PNG, JPEG, TIFF · dosya başına en fazla {MAX_MB} MB · birden çok dosya seçebilirsiniz</p>
          <input ref={inputRef} type="file" multiple accept={ACCEPT} className="hidden" onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }} />
        </div>

        {files.length > 0 && (
          <ul className="divide-y divide-line rounded-xl border border-line text-sm">
            {files.map((f, i) => (
              <li key={i} className="flex items-center justify-between px-4 py-2">
                <span className="truncate">{i + 1}. {f.name}</span>
                <span className="flex items-center gap-3 text-muted">
                  {(f.size / 1024 / 1024).toFixed(1)} MB
                  <button onClick={() => setFiles(files.filter((_, j) => j !== i))} aria-label={`${f.name} dosyasını çıkar`} className="hover:text-bad">✕</button>
                </span>
              </li>
            ))}
          </ul>
        )}

        {err && <ErrorState message={err} />}
        {result && (
          <div className="rounded-xl border border-ok/30 bg-ok-soft p-4 text-sm">
            <p className="font-medium text-ok">{result.created.length} öğrenci kâğıdı işleme kuyruğuna alındı.</p>
            {result.errors.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-bad">{result.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button onClick={() => { reset(); onClose(); }}>Kapat</Button>
          <Button variant="primary" onClick={submit} loading={busy} disabled={!canSubmit}>Yükle ve analiz et</Button>
        </div>
      </div>
    </Modal>
  );
}
