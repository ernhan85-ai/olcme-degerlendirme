# Database schema (assessment module)

PostgreSQL 16, SQLAlchemy 2 models in `backend/app/models/__init__.py`, migration
`backend/alembic/versions/0001_assessment_module_initial_schema.py` (verified: upgrade →
downgrade → upgrade, `alembic check` clean). UUID primary keys everywhere. Every tenant-owned
table has `organization_id` (indexed) and every query filters on it.

`[CORE]` tables are minimal stand-ins for the Phase-1 foundation so the module runs standalone.
When merging into the monorepo, keep the core team's versions and drop these.

```
organizations ─┬─ campuses ─── classes ─── students
               ├─ users ─── user_roles (role, campus_id)            [CORE]
               ├─ subjects, learning_outcomes (code, prerequisite_ids)
               └─ teacher_assignments (teacher, class, subject)

exams ─┬─ exam_classes
       └─ exam_questions (position, points) ─┬─ questions (bank item, answer_type, options)
                                             │      └─ question_outcome_mappings (weight, validated_by)
                                             └─ answer_keys (correct_answer, reference_steps, validated_by/at)

student_submissions ─┬─ submission_files (storage_key, sha256, mime, malware_scan)
                     ├─ processing_jobs (status, attempts, error_code/message, log, provider_is_mock)
                     └─ student_responses (final_answer, confidence, is_correct, score, needs_review,
                          │                 transcription_source, page, bbox)
                          ├─ solution_steps (raw_text, normalized_expr, ocr_confidence, crossed_out,
                          │                  bbox, verdict, edited_by_teacher)
                          └─ error_hypotheses (category, detector, observed_error, inferred_cause,
                               │               alternatives, diagnostic_questions, raw/calibrated
                               │               confidence, llm_explanation(+is_mock), review_status,
                               │               engine_version)
                               └─ evidence_items (kind, description, step_index, page, bbox, verified_by)

teacher_reviews (hypothesis_id SET NULL on re-analysis, response_id, action, original/corrected
                 category, detector, note)      → calibration source
audit_logs     (org, actor, action, entity, details JSON, created_at)
```

Enum types (`exam_status`, `answer_type`, `role_name`, `job_status`, `error_category`,
`review_status`, `step_verdict`) are created once at the top of the migration because several
tables share them.

Mastery (`student_mastery`), interventions and impact tables belong to Phases 4–5. This module
only produces **observed** exam statistics; it never writes mastery estimates.
