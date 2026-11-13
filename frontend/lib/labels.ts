import type { AnswerType, ErrorCategory, ExamStatus, JobStatus, ReviewStatus, StepVerdict } from "./types";

export const ERROR_CATEGORY_TR: Record<ErrorCategory, string> = {
  conceptual_misunderstanding: "Kavram yanılgısı",
  missing_prerequisite: "Eksik ön koşul bilgi",
  arithmetic_error: "İşlem (aritmetik) hatası",
  incorrect_procedure: "Yanlış işlem yolu",
  problem_interpretation: "Problemi yanlış yorumlama",
  incomplete_solution: "Eksik çözüm",
  incorrect_strategy: "Uygun olmayan strateji",
  transfer_difficulty: "Bilgiyi transfer güçlüğü",
  possible_attention_mistake: "Olası dikkat kaynaklı hata",
  insufficient_evidence: "Yetersiz kanıt",
};

export const JOB_STATUS_TR: Record<JobStatus, string> = {
  uploaded: "Yüklendi", queued: "Sırada", processing: "İşleniyor",
  requires_review: "İnceleme gerekiyor", completed: "Tamamlandı", failed: "Başarısız",
};

export const EXAM_STATUS_TR: Record<ExamStatus, string> = {
  draft: "Taslak", extracting: "Sorular çıkarılıyor", in_review: "Öğretmen kontrolünde",
  published: "Yayımlandı", archived: "Arşivlendi",
};

export const REVIEW_STATUS_TR: Record<ReviewStatus, string> = {
  pending: "İnceleme bekliyor", not_required: "Yüksek güven (inceleme isteğe bağlı)",
  approved: "Öğretmen onayladı", modified: "Öğretmen düzeltti", rejected: "Öğretmen reddetti",
};

export const VERDICT_TR: Record<StepVerdict, string> = {
  valid: "Geçerli adım", invalid: "Geçersiz dönüşüm", unverifiable: "Doğrulanamadı", not_checked: "Kontrol edilmedi",
};

export const ANSWER_TYPE_TR: Record<AnswerType, string> = {
  multiple_choice: "Çoktan seçmeli", numeric: "Sayısal cevap", expression: "Cebirsel ifade",
  equation: "Denklem çözümü", open_ended: "Açık uçlu (öğretmen puanlar)",
};

export const ITEM_FLAG_TR: Record<string, string> = {
  cok_zor: "Çok zor (p < 0,20)",
  cok_kolay: "Çok kolay (p > 0,90)",
  dusuk_ayirt_edicilik: "Ayırt edicilik düşük",
  negatif_ayirt_edicilik: "Negatif ayırt edicilik — cevap anahtarını kontrol edin",
};

export function flagLabel(flag: string): string {
  if (ITEM_FLAG_TR[flag]) return ITEM_FLAG_TR[flag];
  const m = flag.match(/^celdirici_(.+)_ust_grubu_cekiyor$/);
  if (m) return `${m[1]} çeldiricisi başarılı öğrencileri çekiyor`;
  return flag;
}

export function pct(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined) return "—";
  return `%${(v * 100).toFixed(digits).replace(".", ",")}`;
}

export function num(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "—";
  return v.toFixed(digits).replace(".", ",");
}

export function trDate(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}
