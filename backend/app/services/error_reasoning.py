"""ENGINE 1 — AI Error Reasoning Engine (rule + SymPy core).

Design principles (see docs/AI_ENGINE_DESIGN.md):
* Observable mistake (what is on paper) is stored separately from the inferred cause.
* Every hypothesis carries evidence pointing at concrete steps / bounding boxes.
* Confidence is a heuristic prior, later calibrated against teacher reviews (calibration.py).
* No psychological or stable-trait inferences. "Possible attention-related mistake" is
  phrased as a one-off observation, never a label on the student.
* Missing handwritten work is never invented: unreadable/absent work -> INSUFFICIENT_EVIDENCE.
* LLM text (if any) is added afterwards as an *unverified* explanation only; it never
  decides the category or correctness.

This module is pure (no DB access) so it is fully unit-testable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp

from app.models import ErrorCategory, StepVerdict
from app.services import math_verify as mv

ENGINE_VERSION = "1.0.0"
UNREADABLE_MESSAGE_TR = "Öğrenci çözümü güvenilir biçimde analiz edilemedi. Öğretmen incelemesi gerekiyor."


# ---------------------------------------------------------------- I/O dataclasses
@dataclass
class StepInput:
    index: int
    raw_text: str
    normalized_expr: str | None = None
    ocr_confidence: float | None = None
    is_crossed_out: bool = False
    page: int | None = None
    bbox: list[float] | None = None

    @property
    def text_for_math(self) -> str:
        return self.normalized_expr or self.raw_text


@dataclass
class ResponseInput:
    answer_type: str
    correct_answer: str
    final_answer: str | None
    answer_confidence: float | None = None
    steps: list[StepInput] = field(default_factory=list)
    reference_steps: list[str] = field(default_factory=list)  # [0] = problem in math form
    options: dict | None = None  # MC: {"A": "text"} or {"A": {"text":..,"misconception":..,"note":..}}
    has_prerequisites: bool = False
    answer_page: int | None = None
    answer_bbox: list[float] | None = None


@dataclass
class EvidenceDraft:
    kind: str
    description: str
    verified_by: str
    step_index: int | None = None
    page: int | None = None
    bbox: list[float] | None = None


@dataclass
class HypothesisDraft:
    category: ErrorCategory
    detector: str
    observed_error: str
    inferred_cause: str
    raw_confidence: float
    evidence: list[EvidenceDraft] = field(default_factory=list)
    alternative_explanations: list[str] = field(default_factory=list)
    diagnostic_questions: list[str] = field(default_factory=list)
    is_primary: bool = False


@dataclass
class StepVerdictOut:
    index: int
    verdict: StepVerdict
    detail: str | None = None


@dataclass
class AnalysisResult:
    is_correct: bool | None
    needs_review: bool
    review_reasons: list[str]
    step_verdicts: list[StepVerdictOut]
    hypotheses: list[HypothesisDraft]
    engine_version: str = ENGINE_VERSION


# ---------------------------------------------------------------- templates (TR)
DIAGNOSTIC_TEMPLATES: dict[ErrorCategory, list[str]] = {
    ErrorCategory.CONCEPTUAL_MISUNDERSTANDING: [
        "Bu işlemi neden bu şekilde yaptığını kendi cümlelerinle açıklar mısın?",
        "Aynı kavramı içeren daha basit bir örneği modelle (şekil/sayı doğrusu) gösterebilir misin?",
    ],
    ErrorCategory.MISSING_PREREQUISITE: [
        "Ön koşul kazanımı yoklayan 2-3 kısa soru sorun (bağlamdan bağımsız).",
    ],
    ErrorCategory.ARITHMETIC_ERROR: [
        "Aynı işlemi başka bir yolla (ör. alt alta) yeniden hesaplayabilir misin?",
        "Bulduğun sonucu yerine koyarak kontrol eder misin?",
    ],
    ErrorCategory.INCORRECT_PROCEDURE: [
        "Bu adımda hangi kuralı uyguladın? Kuralı bir örnekle gösterir misin?",
        "Eşitliğin iki tarafına aynı işlemi uyguladığını nasıl kontrol edersin?",
    ],
    ErrorCategory.PROBLEM_INTERPRETATION: [
        "Soruda verilenleri ve isteneni kendi cümlelerinle yazar mısın?",
    ],
    ErrorCategory.INCOMPLETE_SOLUTION: [
        "Çözümünün son adımından sonra ne yapman gerekiyordu?",
        "Sorunun tam olarak ne istediğini yeniden okuyup cevabını kontrol eder misin?",
    ],
    ErrorCategory.INCORRECT_STRATEGY: [
        "Bu soruyu çözmek için başka hangi yolu deneyebilirdin?",
    ],
    ErrorCategory.TRANSFER_DIFFICULTY: [
        "Aynı kazanımı farklı bir bağlamda soran bir soru deneyin.",
    ],
    ErrorCategory.POSSIBLE_ATTENTION_MISTAKE: [
        "Çözümünde bulduğun sonuç ile cevap olarak yazdığını karşılaştırır mısın?",
    ],
    ErrorCategory.INSUFFICIENT_EVIDENCE: [
        "Öğrenciden çözümünü sözlü olarak açıklamasını isteyin.",
        "Benzer bir soruyu işlem adımlarını yazarak çözmesini isteyin.",
    ],
}


def _cat_value(c: ErrorCategory | str) -> str:
    return c.value if isinstance(c, ErrorCategory) else c


# ---------------------------------------------------------------- transition classifiers
_FRACTION_ADD = re.compile(r"(-?\d+)\s*/\s*(\d+)\s*\+\s*(-?\d+)\s*/\s*(\d+)")
_DISTRIB = re.compile(r"(-?\d*)\s*\*?\s*\(\s*([^()+\-]+)\s*([+\-])\s*([^()]+?)\s*\)")


def _single_value(p: mv.Parsed) -> sp.Expr | None:
    """If p is 'x = number' (or a pure number), return that number."""
    if p.kind == "expr":
        return sp.nsimplify(p.expr) if not p.free_symbols else None
    sol = mv.solution_set(p)
    if sol and len(sol) == 1:
        v = next(iter(sol))
        return v if v.is_number else None
    return None


def _is_resolved(p: mv.Parsed) -> bool:
    """'x = 5' or '5' is resolved; '2x = 10' is not."""
    if p.kind == "expr":
        return not p.free_symbols
    for a, b in ((p.lhs, p.rhs), (p.rhs, p.lhs)):
        if isinstance(a, sp.Symbol) and not b.free_symbols:
            return True
    return False


def _detect_fraction_add(prev_text: str, cur: mv.Parsed) -> tuple[str, str] | None:
    m = _FRACTION_ADD.search(mv.normalize_text(prev_text))
    if not m:
        return None
    a, b, c, d = (int(g) for g in m.groups())
    wrong = sp.Rational(a + c, b + d)
    val = _single_value(cur)
    if val is None:
        # maybe cur is still an equation with that wrong fraction somewhere
        z = cur.as_zero_form()
        if any(sp.nsimplify(t) == wrong for t in sp.preorder_traversal(z) if getattr(t, "is_number", False)):
            val = wrong
    if val is not None and sp.nsimplify(val) == wrong and wrong != sp.Rational(a, b) + sp.Rational(c, d):
        return (f"{a}/{b} + {c}/{d}", f"{a + c}/{b + d}")
    return None


def _detect_sign_transposition(prev: mv.Parsed, cur: mv.Parsed) -> sp.Expr | None:
    if prev.kind != "eq" or cur.kind != "eq":
        return None
    z0, z1 = prev.as_zero_form(), cur.as_zero_form()
    if z1 == 0:
        return None
    # use un-combined terms of each side so "3x+5=20" yields 3x, 5, -20 (not 3x, -15)
    terms = list(sp.Add.make_args(sp.expand(prev.lhs))) + [-t for t in sp.Add.make_args(sp.expand(prev.rhs))]
    for t in terms:
        cand = sp.expand(z0 - 2 * t)
        if cand == 0:
            continue
        ratio = sp.simplify(cand / z1)
        if ratio.is_number and ratio != 0:
            return t
    return None


def _detect_partial_distribution(prev_text: str, cur: mv.Parsed) -> str | None:
    t = mv.normalize_text(prev_text)
    m = _DISTRIB.search(t)
    if not m:
        return None
    k, a, op, b = m.groups()
    k = k or "1"
    if k == "-":
        k = "-1"
    wrong_inner = f"({k})*({a}){op}({b})"  # factor applied only to the first term
    wrong_text = t[: m.start()] + wrong_inner + t[m.end():]
    wrong = mv.try_parse(wrong_text)
    if wrong is None:
        return None
    eq = mv.equivalent(wrong, cur)
    original_ok = mv.equivalent(mv.parse_math(t), cur)
    if eq and not original_ok:
        return m.group(0)
    return None


def _detect_inverse_operation(prev: mv.Parsed, cur: mv.Parsed) -> str | None:
    if prev.kind != "eq":
        return None
    val = _single_value(cur)
    if val is None:
        return None
    for lhs, rhs in ((prev.lhs, prev.rhs), (prev.rhs, prev.lhs)):
        if rhs.free_symbols:
            continue
        r = sp.nsimplify(rhs)
        syms = list(lhs.free_symbols)
        if len(syms) != 1:
            continue
        x = syms[0]
        lin = sp.Poly(sp.expand(lhs), x) if sp.expand(lhs).is_polynomial(x) else None
        if lin is None or lin.degree() != 1:
            continue
        coef, const = (sp.nsimplify(c) for c in lin.all_coeffs())
        if const == 0 and coef != 1:  # c*x = r ; correct r/c
            if val in {r - coef, r + coef, r * coef} and val != r / coef:
                return f"{coef}·x = {r} → bölme yerine farklı işlem uygulanmış"
        if coef == 1 and const != 0:  # x + c = r ; correct r - c
            if val in {r + const, r * const} and val != r - const:
                return f"x {'+' if const > 0 else '-'} {abs(const)} = {r} → ters işlem yerine aynı işlem uygulanmış"
    return None


def _numeric_slip(prev: mv.Parsed, cur: mv.Parsed) -> bool:
    """Heuristic: structure preserved, only numbers off (e.g. 3x = 15 -> x = 6)."""
    if prev.kind != cur.kind:
        return False
    if prev.kind == "expr":
        return not prev.free_symbols and not cur.free_symbols
    v0, v1 = _single_value(prev), _single_value(cur)
    if v0 is not None and v1 is not None:
        return bool(abs(v0 - v1) <= max(2, abs(v0) * 0.25))
    try:
        x = sorted(prev.free_symbols | cur.free_symbols, key=str)
        if len(x) != 1:
            return False
        d0 = sp.Poly(prev.as_zero_form(), x[0]).degree()
        d1 = sp.Poly(cur.as_zero_form(), x[0]).degree()
        return d0 == d1
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------- main engine
class ErrorReasoningEngine:
    def __init__(self, ocr_min_confidence: float = 0.6, review_threshold: float = 0.7):
        self.ocr_min = ocr_min_confidence
        self.review_threshold = review_threshold

    # public ---------------------------------------------------------
    def analyze(self, r: ResponseInput) -> AnalysisResult:
        reasons: list[str] = []
        verdicts: list[StepVerdictOut] = []
        hyps: list[HypothesisDraft] = []

        active = [s for s in r.steps if not s.is_crossed_out]
        crossed = [s for s in r.steps if s.is_crossed_out]
        for s in crossed:
            verdicts.append(StepVerdictOut(s.index, StepVerdict.NOT_CHECKED, "Üstü çizilmiş adım; analize dahil edilmedi."))

        low_ocr = [s for s in active if s.ocr_confidence is not None and s.ocr_confidence < self.ocr_min]
        if low_ocr:
            reasons.append(f"{len(low_ocr)} adımda el yazısı tanıma güveni düşük.")
        if r.answer_confidence is not None and r.answer_confidence < self.ocr_min:
            reasons.append("Cevap tanıma güveni düşük.")

        final = r.final_answer
        if (final is None or not final.strip()) and active and r.answer_type != "multiple_choice":
            last = mv.try_parse(active[-1].text_for_math)
            if last is not None and _is_resolved(last):
                final = active[-1].text_for_math
                reasons.append("Ayrı bir cevap alanı bulunamadı; son çözüm adımı cevap kabul edildi.")

        is_correct = mv.answers_match(final, r.correct_answer, r.answer_type)
        if is_correct is None:
            reasons.append("Cevabın doğruluğu otomatik olarak belirlenemedi.")

        # --- step chain verification
        parsed: list[tuple[StepInput, mv.Parsed | None]] = []
        for s in active:
            p = mv.try_parse(s.text_for_math)
            parsed.append((s, p))
            if p is None:
                verdicts.append(StepVerdictOut(s.index, StepVerdict.UNVERIFIABLE, "Matematiksel ifade olarak okunamadı."))

        first_invalid: tuple[StepInput, mv.Parsed, StepInput, mv.Parsed] | None = None
        prev_s: StepInput | None = None
        prev_p: mv.Parsed | None = None
        problem = mv.try_parse(r.reference_steps[0]) if r.reference_steps else None
        setup_mismatch: StepInput | None = None

        for i, (s, p) in enumerate(parsed):
            if p is None:
                continue
            if prev_p is None:
                if i == 0 and problem is not None and problem.kind == p.kind:
                    eq = mv.equivalent(problem, p)
                    if eq is False:
                        setup_mismatch = s
                        verdicts.append(StepVerdictOut(s.index, StepVerdict.INVALID, "Sorudaki ifadeyle denk değil (soru yanlış aktarılmış olabilir)."))
                    else:
                        verdicts.append(StepVerdictOut(s.index, StepVerdict.VALID, "Soru ifadesiyle denk."))
                else:
                    verdicts.append(StepVerdictOut(s.index, StepVerdict.VALID if problem is None else StepVerdict.NOT_CHECKED, "İlk adım."))
            else:
                eq = mv.equivalent(prev_p, p)
                if eq is True:
                    verdicts.append(StepVerdictOut(s.index, StepVerdict.VALID, "Önceki adımla denk (SymPy)."))
                elif eq is False:
                    verdicts.append(StepVerdictOut(s.index, StepVerdict.INVALID, "Önceki adımla denk değil (SymPy)."))
                    if first_invalid is None:
                        first_invalid = (prev_s, prev_p, s, p)
                else:
                    verdicts.append(StepVerdictOut(s.index, StepVerdict.UNVERIFIABLE, "Denklik otomatik doğrulanamadı."))
            prev_s, prev_p = s, p

        verdicts.sort(key=lambda v: v.index)
        parsed_ok = [x for x in parsed if x[1] is not None]

        # --- hypotheses
        if is_correct is True:
            if first_invalid is not None:
                ps, _, cs, _ = first_invalid
                hyps.append(HypothesisDraft(
                    category=ErrorCategory.INCORRECT_PROCEDURE,
                    detector="correct_answer_invalid_step",
                    observed_error=f"Cevap doğru ancak {cs.index + 1}. adımdaki dönüşüm geçersiz.",
                    inferred_cause="Ara adımlarda birbirini telafi eden hatalar ya da adımların eksik/yanlış aktarılması olabilir.",
                    raw_confidence=0.4,
                    evidence=[self._ev_transition(ps, cs, "Önceki adımla denk olmayan dönüşüm.")],
                    alternative_explanations=["El yazısı tanıma hatası", "Öğrenci adımları zihinden yapıp eksik yazmış olabilir"],
                ))
        elif r.answer_type == "multiple_choice" and not parsed_ok:
            hyps.append(self._mc_hypothesis(r, final))
        elif not active or not parsed_ok:
            hyps.append(HypothesisDraft(
                category=ErrorCategory.INSUFFICIENT_EVIDENCE,
                detector="no_readable_work",
                observed_error="Okunabilir çözüm adımı yok." if active else "Çözüm adımı yazılmamış.",
                inferred_cause=UNREADABLE_MESSAGE_TR if active else "Hatanın nedeni hakkında çıkarım yapmak için kanıt yetersiz.",
                raw_confidence=0.95,
                evidence=[EvidenceDraft("missing_work", "Çözüm alanında analiz edilebilir işlem bulunamadı.", "ocr",
                                        page=r.answer_page, bbox=r.answer_bbox)],
            ))
            if active:
                reasons.append(UNREADABLE_MESSAGE_TR)
        elif is_correct is False:
            if setup_mismatch is not None:
                hyps.append(HypothesisDraft(
                    category=ErrorCategory.PROBLEM_INTERPRETATION,
                    detector="setup_mismatch",
                    observed_error=f"İlk adım ({setup_mismatch.raw_text}) sorudaki ifadeyle ({r.reference_steps[0]}) denk değil.",
                    inferred_cause="Soru yanlış okunmuş ya da yanlış aktarılmış olabilir.",
                    raw_confidence=0.65,
                    evidence=[self._ev_step(setup_mismatch, "Soru ifadesiyle karşılaştırıldı (SymPy).", "sympy")],
                    alternative_explanations=["Sayının kopyalanmasında dikkat hatası", "El yazısı tanıma hatası"],
                ))
            if first_invalid is not None:
                hyps.extend(self._classify_transition(*first_invalid, has_prereq=r.has_prerequisites))
            elif setup_mismatch is None:
                hyps.extend(self._all_valid_but_wrong(r, final, parsed_ok))

        for h in hyps:
            if not h.diagnostic_questions:
                h.diagnostic_questions = list(DIAGNOSTIC_TEMPLATES.get(h.category, []))
            h.raw_confidence = self._apply_ocr_penalty(h, active)
        if hyps:
            max(hyps, key=lambda h: h.raw_confidence).is_primary = True

        needs_review = bool(reasons) or any(h.raw_confidence < self.review_threshold for h in hyps)
        if any(h.category == ErrorCategory.INSUFFICIENT_EVIDENCE for h in hyps):
            needs_review = True
        return AnalysisResult(is_correct, needs_review, reasons, verdicts, hyps)

    # helpers -------------------------------------------------------
    def _apply_ocr_penalty(self, h: HypothesisDraft, active: list[StepInput]) -> float:
        idx = {e.step_index for e in h.evidence if e.step_index is not None}
        confs = [s.ocr_confidence for s in active if s.index in idx and s.ocr_confidence is not None]
        factor = min(confs) if confs else 1.0
        # an unreadable step weakens the hypothesis, but never below 50% of prior
        return round(max(0.05, min(0.99, h.raw_confidence * (0.5 + 0.5 * factor))), 3)

    @staticmethod
    def _ev_step(s: StepInput, desc: str, by: str) -> EvidenceDraft:
        return EvidenceDraft("step", desc, by, step_index=s.index, page=s.page, bbox=s.bbox)

    @staticmethod
    def _ev_transition(prev: StepInput, cur: StepInput, desc: str, by: str = "sympy") -> EvidenceDraft:
        return EvidenceDraft("step_transition", f"{desc} [{prev.raw_text}] → [{cur.raw_text}]", by,
                             step_index=cur.index, page=cur.page, bbox=cur.bbox)

    def _classify_transition(self, ps: StepInput, pp: mv.Parsed, cs: StepInput, cp: mv.Parsed,
                             has_prereq: bool) -> list[HypothesisDraft]:
        out: list[HypothesisDraft] = []
        frac = _detect_fraction_add(ps.text_for_math, cp)
        if frac:
            out.append(HypothesisDraft(
                category=ErrorCategory.CONCEPTUAL_MISUNDERSTANDING,
                detector="fraction_add_num_den",
                observed_error=f"{frac[0]} işleminde paylar ve paydalar ayrı ayrı toplanmış ({frac[1]}).",
                inferred_cause="Kesirlerde toplama için ortak payda gerektiği kavranmamış olabilir.",
                raw_confidence=0.85,
                evidence=[self._ev_transition(ps, cs, "Pay+pay / payda+payda kalıbı tespit edildi.", "rule")],
                alternative_explanations=["Tek seferlik işlem kayması (aynı hata başka sorularda da görülüyorsa olasılık düşer)"],
                diagnostic_questions=["1/2 + 1/2 kaç eder? Bir pizza modeliyle gösterir misin?",
                                      "1/3 + 1/6 işlemini adım adım yapar mısın?"],
            ))
            if has_prereq:
                out.append(HypothesisDraft(
                    category=ErrorCategory.MISSING_PREREQUISITE,
                    detector="fraction_add_num_den",
                    observed_error="Kesir toplama hatası, bu sorunun ön koşul kazanımıyla ilişkili.",
                    inferred_cause="Ön koşul kazanım (kesirlerle toplama) yeterince pekişmemiş olabilir.",
                    raw_confidence=0.55,
                    evidence=[self._ev_transition(ps, cs, "Ön koşul kazanımına ait işlem hatası.", "rule")],
                ))
            return out

        term = _detect_sign_transposition(pp, cp)
        if term is not None:
            out.append(HypothesisDraft(
                category=ErrorCategory.INCORRECT_PROCEDURE,
                detector="sign_transposition",
                observed_error=f"'{term}' terimi eşitliğin diğer tarafına geçerken işareti değiştirilmemiş.",
                inferred_cause="Eşitliğin iki tarafına aynı işlemi uygulama (ters işlem) kuralı hatalı uygulanmış olabilir.",
                raw_confidence=0.8,
                evidence=[self._ev_transition(ps, cs, "Tek bir terimin işareti ters çevrildiğinde adımlar denk oluyor (SymPy).")],
                alternative_explanations=["Tek seferlik dikkat hatası", "El yazısında '+'/'-' karışıklığı (OCR)"],
            ))
            return out

        dist = _detect_partial_distribution(ps.text_for_math, cp)
        if dist:
            out.append(HypothesisDraft(
                category=ErrorCategory.INCORRECT_PROCEDURE,
                detector="partial_distribution",
                observed_error=f"{dist} ifadesinde çarpan parantez içindeki yalnızca ilk terime dağıtılmış.",
                inferred_cause="Dağılma özelliği eksik uygulanmış olabilir.",
                raw_confidence=0.78,
                evidence=[self._ev_transition(ps, cs, "Çarpan yalnızca ilk terime uygulandığında adımlar denk oluyor (SymPy).")],
                alternative_explanations=["Dağılma özelliğine ilişkin kavramsal yanılgı", "Dikkat hatası"],
            ))
            return out

        inv = _detect_inverse_operation(pp, cp)
        if inv:
            out.append(HypothesisDraft(
                category=ErrorCategory.INCORRECT_PROCEDURE,
                detector="inverse_operation",
                observed_error=inv,
                inferred_cause="Bilinmeyeni yalnız bırakmak için gereken ters işlem karıştırılmış olabilir.",
                raw_confidence=0.75,
                evidence=[self._ev_transition(ps, cs, "Sonuç, yanlış ters işlemle elde edilen değere eşit.", "rule")],
                alternative_explanations=["Denklem kavramına ilişkin kavramsal yanılgı", "Aritmetik hata"],
            ))
            return out

        if _numeric_slip(pp, cp):
            out.append(HypothesisDraft(
                category=ErrorCategory.ARITHMETIC_ERROR,
                detector="numeric_slip",
                observed_error=f"{cs.index + 1}. adımda yapı korunmuş ancak sayısal sonuç hatalı.",
                inferred_cause="Dört işlem sırasında hesaplama hatası yapılmış olabilir.",
                raw_confidence=0.62,
                evidence=[self._ev_transition(ps, cs, "Adımlar denk değil; ifade yapısı aynı, sayılar farklı (SymPy).")],
                alternative_explanations=["İşlem prosedürü hatası", "El yazısı tanıma hatası (rakam karışıklığı)"],
            ))
            return out

        out.append(HypothesisDraft(
            category=ErrorCategory.INCORRECT_PROCEDURE,
            detector="unclassified_invalid_transition",
            observed_error=f"{cs.index + 1}. adımdaki dönüşüm matematiksel olarak geçersiz.",
            inferred_cause="Hatanın türü kurallarla belirlenemedi; öğretmen değerlendirmesi önerilir.",
            raw_confidence=0.45,
            evidence=[self._ev_transition(ps, cs, "Önceki adımla denk değil (SymPy).")],
            alternative_explanations=["Kavramsal yanılgı", "Aritmetik hata", "Yanlış strateji"],
        ))
        return out

    def _all_valid_but_wrong(self, r: ResponseInput, final: str | None,
                             parsed_ok: list[tuple[StepInput, mv.Parsed]]) -> list[HypothesisDraft]:
        last_s, last_p = parsed_ok[-1]
        last_correct = mv.answers_match(last_s.text_for_math, r.correct_answer, r.answer_type)
        if last_correct and final is not None and final.strip() and final != last_s.text_for_math:
            return [HypothesisDraft(
                category=ErrorCategory.POSSIBLE_ATTENTION_MISTAKE,
                detector="answer_transcription",
                observed_error=f"Çözümde doğru sonuç ({last_s.raw_text}) bulunmuş, ancak cevap olarak '{final}' yazılmış.",
                inferred_cause="Sonuç cevap alanına aktarılırken hata yapılmış olabilir (tek seferlik gözlem).",
                raw_confidence=0.6,
                evidence=[self._ev_step(last_s, "Son adım anahtarla denk (SymPy).", "sympy"),
                          EvidenceDraft("final_answer", f"Cevap alanı: {final}", "ocr", page=r.answer_page, bbox=r.answer_bbox)],
                alternative_explanations=["Cevap alanında el yazısı tanıma hatası", "Soru farklı bir biçimde sonuç istiyor olabilir"],
            )]
        if not _is_resolved(last_p):
            return [HypothesisDraft(
                category=ErrorCategory.INCOMPLETE_SOLUTION,
                detector="unresolved_last_step",
                observed_error=f"Tüm adımlar geçerli ancak çözüm '{last_s.raw_text}' adımında bırakılmış.",
                inferred_cause="Çözüm tamamlanmamış; zaman yetersizliği veya son adımın bilinmemesi olabilir.",
                raw_confidence=0.72,
                evidence=[self._ev_step(last_s, "Son adım henüz sonuca ulaşmamış.", "sympy")],
                alternative_explanations=["Zaman yetersizliği", "Sonraki adımın nasıl yapılacağının bilinmemesi"],
            )]
        return [HypothesisDraft(
            category=ErrorCategory.INCORRECT_STRATEGY,
            detector="valid_chain_wrong_target",
            observed_error="Adımlar kendi içinde tutarlı fakat sorunun istediğinden farklı bir sonuca ulaşılmış.",
            inferred_cause="Soru farklı yorumlanmış veya uygun olmayan bir strateji seçilmiş olabilir.",
            raw_confidence=0.5,
            evidence=[self._ev_step(last_s, "Son adım anahtarla denk değil.", "sympy")],
            alternative_explanations=["Problemi yorumlama hatası", "Cevap anahtarında hata (kontrol edin)"],
        )]

    def _mc_hypothesis(self, r: ResponseInput, final: str | None) -> HypothesisDraft:
        choice = (final or "").strip().upper()[:1]
        opt = (r.options or {}).get(choice)
        if isinstance(opt, dict) and opt.get("misconception"):
            try:
                cat = ErrorCategory(opt["misconception"])
            except ValueError:
                cat = ErrorCategory.CONCEPTUAL_MISUNDERSTANDING
            return HypothesisDraft(
                category=cat, detector="mc_distractor_tag",
                observed_error=f"'{choice}' seçeneği işaretlenmiş (doğru: {r.correct_answer}).",
                inferred_cause=opt.get("note") or "Bu çeldirici belirli bir yanılgıyla ilişkilendirilmiş.",
                raw_confidence=0.45,
                evidence=[EvidenceDraft("final_answer", f"Seçilen çeldirici: {choice}", "rule", page=r.answer_page, bbox=r.answer_bbox)],
                alternative_explanations=["Tahmin", "Dikkat hatası", "Çözüm yazılmadığı için doğrulanamaz"],
            )
        return HypothesisDraft(
            category=ErrorCategory.INSUFFICIENT_EVIDENCE, detector="mc_no_work",
            observed_error=f"Yanlış seçenek ('{choice or '-'}') işaretlenmiş; çözüm yazılmamış.",
            inferred_cause="Yalnızca işaretlenen seçenekten hata nedeni çıkarılamaz.",
            raw_confidence=0.9,
            evidence=[EvidenceDraft("final_answer", f"İşaretlenen: {choice or 'boş'}", "ocr", page=r.answer_page, bbox=r.answer_bbox)],
        )
