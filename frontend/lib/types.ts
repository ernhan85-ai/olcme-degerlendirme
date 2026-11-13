// Mirrors backend/app/schemas/__init__.py — keep in sync.
export type UUID = string;

export type AnswerType = "multiple_choice" | "numeric" | "expression" | "equation" | "open_ended";
export type ExamStatus = "draft" | "extracting" | "in_review" | "published" | "archived";
export type JobStatus = "uploaded" | "queued" | "processing" | "requires_review" | "completed" | "failed";
export type ReviewStatus = "pending" | "not_required" | "approved" | "modified" | "rejected";
export type StepVerdict = "valid" | "invalid" | "unverifiable" | "not_checked";
export type ErrorCategory =
  | "conceptual_misunderstanding" | "missing_prerequisite" | "arithmetic_error" | "incorrect_procedure"
  | "problem_interpretation" | "incomplete_solution" | "incorrect_strategy" | "transfer_difficulty"
  | "possible_attention_mistake" | "insufficient_evidence";

export interface IdName { id: UUID; name: string }
export interface ClassOut { id: UUID; name: string; grade_level: number; campus_id: UUID }
export interface OutcomeOut { id: UUID; code: string; description: string; grade_level: number; subject_id: UUID }
export interface Lookups { subjects: IdName[]; classes: ClassOut[]; outcomes: OutcomeOut[] }
export interface Student { id: UUID; full_name: string; student_number: string; class_id: UUID | null }
export interface Me { id: UUID; full_name: string; email: string; roles: string[] }

export interface QuestionIn {
  position: number; stem_text: string; answer_type: AnswerType; options?: Record<string, unknown> | null;
  points: number; correct_answer: string; reference_steps: string[]; outcome_ids: UUID[];
}
export interface QuestionOut {
  exam_question_id: UUID; question_id: UUID; position: number; points: number; stem_text: string;
  answer_type: AnswerType; options: Record<string, unknown> | null; correct_answer: string | null;
  reference_steps: string[]; key_validated: boolean; outcome_ids: UUID[];
}
export interface Exam {
  id: UUID; title: string; subject_id: UUID; subject_name: string | null; grade_level: number; class_ids: UUID[];
  exam_date: string; status: ExamStatus; has_booklet: boolean; question_count: number;
  submission_count: number; pending_review_count: number; created_at: string;
}
export interface ExamDetail extends Exam { questions: QuestionOut[]; publish_blockers: string[] }

export interface Job {
  id: UUID; status: JobStatus; attempts: number; error_code: string | null; error_message: string | null;
  provider_name: string | null; provider_is_mock: boolean; log: { at: string; status: JobStatus; note: string }[];
  updated_at: string;
}
export interface SubmissionFile { id: UUID; original_name: string; mime_type: string; size_bytes: number; page_order: number; malware_scan: string }
export interface Submission {
  id: UUID; exam_id: UUID; student: Student; total_score: number | null; max_score: number | null;
  job: Job | null; files: SubmissionFile[]; needs_review_count: number; created_at: string;
}
export interface UploadResult { created: Submission[]; errors: string[] }

export interface Step {
  id: UUID; step_index: number; raw_text: string; normalized_expr: string | null; ocr_confidence: number | null;
  is_crossed_out: boolean; page: number | null; bbox: number[] | null; verdict: StepVerdict;
  verdict_detail: string | null; edited_by_teacher: boolean;
}
export interface Evidence { id: UUID; kind: string; description: string; step_index: number | null; page: number | null; bbox: number[] | null; verified_by: string }
export interface Hypothesis {
  id: UUID; category: ErrorCategory; detector: string; observed_error: string; inferred_cause: string;
  alternative_explanations: string[]; diagnostic_questions: string[]; raw_confidence: number;
  calibrated_confidence: number; is_primary: boolean; llm_explanation: string | null;
  llm_explanation_is_mock: boolean; review_status: ReviewStatus; engine_version: string; evidence: Evidence[];
}
export interface ResponseAnalysis {
  id: UUID; submission_id: UUID; student: Student; exam_id: UUID; exam_title: string; question: QuestionOut;
  final_answer: string | null; answer_confidence: number | null; is_correct: boolean | null; score: number | null;
  needs_review: boolean; review_reason: string | null; transcription_source: "ai" | "teacher";
  source_page: number | null; source_bbox: number[] | null; files: SubmissionFile[]; steps: Step[];
  hypotheses: Hypothesis[]; provider_is_mock: boolean;
}
export interface ReviewQueueItem {
  response_id: UUID; exam_id: UUID; exam_title: string; student_name: string; position: number;
  reason: string | null; primary_category: ErrorCategory | null; confidence: number | null;
}
export interface ItemStat {
  exam_question_id: UUID; position: number; n: number; difficulty_p: number | null;
  discrimination_rpbis: number | null; discrimination_d: number | null; flags: string[];
  distractors: Record<string, { upper: number; lower: number; total: number }> | null;
  error_categories: Record<string, number>;
}
export interface ItemAnalysis {
  exam_id: UUID; n_students: number; n_items: number; mean_pct: number | null; sd_pct: number | null;
  reliability: number | null; reliability_method: string; sem_pct: number | null; warnings: string[];
  items: ItemStat[]; note: string;
}
export interface OutcomeRow {
  outcome_id: UUID; code: string; description: string; class_observed_pct: number | null; n_items: number;
  students_below_50: number; top_error_category: ErrorCategory | null;
}
export interface OutcomeReport { exam_id: UUID; rows: OutcomeRow[]; note: string }
