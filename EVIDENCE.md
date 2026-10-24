# Capstone Evidence

This document maps the implementation to the capstone requirements.
Statuses describe the evidence currently available in this repository.
A passing unit test does not imply that an external production service
or a complete real-world dataset has been demonstrated.

## 1. Structured Metadata and Confidence

**Status: Partial**

Evidence:
- `tests/test_image_schema.py`
  - `test_valid_image_metadata`
  - `test_confidence_must_be_between_zero_and_one`
  - `test_unknown_fields_are_rejected`
- `tests/test_metadata_provider.py`
  - `test_mock_provider_returns_valid_metadata`
  - `test_mock_provider_obeys_metadata_schema`
- `tests/test_images_api.py`
  - `test_analyze_image_persists_metadata_and_review_flag`
  - Confidence boundary cases at 0.45, 0.69, 0.70, and 0.96.

Limitation:
The configured metadata provider is a mock provider. It does not inspect
image pixels or perform real vision-model inference. Schema validation
is implemented, but real vision output validation is not demonstrated.

## 2. Low-Confidence Review

**Status: Verified for the implemented threshold logic**

Evidence:
- `tests/test_confidence_review.py`
  - `test_requires_review`
  - `test_custom_threshold`
- `tests/test_images_api.py`
  - `test_analyze_image_persists_metadata_and_review_flag`

The default review boundary is 0.70: confidence values below 0.70
require review; 0.70 and above do not under the tested configuration.

## 3. Batch Processing and Retries

**Status: Partial**

Evidence:
- `tests/test_batch_jobs_api.py`
  - Batch-job creation, retrieval, invalid payload, and missing-image tests.
- `tests/test_batch_job_model.py`
  - Default values and progress/failure tracking.
- `tests/test_batch_processor.py`
  - `test_process_batch_job_success`
  - `test_process_batch_job_retries_missing_file`
  - `test_process_batch_job_rejects_mock_metadata`

Limitation:
Retry and failure-handling behavior is tested. A successful batch run
using a genuine vision model across the required image corpus has not
been demonstrated. Mock metadata is deliberately rejected as real
image analysis.

## 4. Per-Call Vision and Embedding Cost Tracking

**Status: Not implemented**

Per-call vision and embedding cost persistence and budget enforcement
are not currently implemented.

## 5. Image and Post Embeddings with Ranked Suggestions

**Status: Partial**

Evidence:
- `tests/test_embedding_provider.py`
  - `test_openai_provider_returns_embeddings_in_input_order`
  - `test_openai_provider_returns_empty_list_without_api_call`
  - `test_openai_provider_rejects_blank_text`
- `tests/test_matching_service.py`
  - `test_match_ranks_posts_by_similarity`
  - `test_match_returns_no_match_below_threshold`

Limitation:
The local matching baseline uses lexical token statistics. The optional
OpenAI provider generates text embeddings. A complete persisted image
and post embedding lifecycle, including image embeddings, is not
implemented or demonstrated.

## 6. Semantic Matching

**Status: Partial**

Evidence:
- `tests/test_matching_service.py`
  - `test_match_ranks_posts_by_similarity`

Limitation:
The lexical baseline supports limited token normalization. It does not
establish reliable semantic equivalence for concepts such as
"red fox" and "Vulpes vulpes". The optional text-embedding provider
does not provide image-pixel understanding.

## 7. Mismatch Guard

**Status: Verified for the tested wolf/fox case**

Evidence:
- `tests/test_matching_service.py`
  - `test_match_rejects_explicit_wolf_fox_mismatch`

Limitation:
The test demonstrates the specific implemented mismatch case.
It does not establish comprehensive mismatch detection across all
subjects and categories.

## 8. No-Confident-Match Behavior

**Status: Verified for the matching threshold behavior**

Evidence:
- `tests/test_matching_service.py`
  - `test_match_returns_no_match_below_threshold`
  - `test_match_handles_no_blog_posts`

The matching service returns no match when no candidate reaches the
configured threshold or when there are no candidate posts.

## 9. Database Models, Relationships, and Indexes

**Status: Partial**

Implemented models include images, blog posts, batch jobs, and
match suggestions. PostgreSQL persistence and Alembic migrations
are part of the project.

Evidence:
- `tests/test_database_config.py`
  - `test_image_table_is_registered`
  - `test_database_engine_configuration`
- `tests/test_batch_job_model.py`
  - Model default and failure-state tests.
- `tests/test_matching_service.py`
  - Matching behavior tests.

Limitation:
This evidence does not establish that every database model, index,
relationship, and persistence requirement in the capstone specification
has been independently verified. Review the migrations and database
schema before claiming full compliance.

## 10. API and Human Review Workflow

**Status: Partial**

Implemented API routes include:
- `GET /images/{image_id}/matches`
- `GET /match-suggestions`
- `POST /match-suggestions/{suggestion_id}/review`

The review workflow supports pending, approved, and rejected statuses,
with an optional decision reason and protection against reviewing an
already-reviewed suggestion.

Evidence:
The review workflow was implemented and manually exercised during
development. The current collected pytest suite contains no dedicated
match-suggestion review test module.

Limitation:
Add reproducible automated tests for listing, filtering, approving,
rejecting, and duplicate-review protection before treating this
workflow as fully test-verified.

## 11. Labeled Evaluation Dataset

**Status: Partial**

Evidence:
- `scripts/evaluate.py`
- Ten manually labeled synthetic evaluation cases.
- README reports:
  - Top-1 precision: 7/10 = 70.0%.
  - Accepted matches: 5/10 = 50.0%.
  - Precision among accepted matches: 5/5 = 100.0%.

Limitation:
The synthetic evaluation does not meet the specified corpus requirement
of at least 40 images across 4 or more categories and at least 10 posts
with labeled correct images. The reported metrics are not production
accuracy measurements.

## 12. Documentation and Submission Files

**Status: In progress**

Present:
- `README.md`
- `.env.example`
- `capstone.yaml`
- `EVIDENCE.md`

Still to prepare:
- `BUILDLOG.md`

The README documents setup, migrations, API routes, matching behavior,
evaluation results, and current limitations.

## Behavioral Probe Summary

| Probe | Current evidence | Status |
|---|---|---|
| Batch processing with real vision metadata | Mock metadata is rejected; no real vision provider | Not demonstrated |
| Red fox ranks above wolf and dog | Explicit wolf/fox mismatch unit test exists | Partial |
| Wolf candidate rejected for fox | `test_match_rejects_explicit_wolf_fox_mismatch` | Verified for this case |
| No suitable image returns no match | No-match threshold tests | Verified for tested cases |
| Evaluation reproduces README metrics | `scripts/evaluate.py` provides a synthetic evaluation | Reproducible baseline |
| Every AI call has cost attribution | Cost tracking is not implemented | Not implemented |

## Final Notes

The project is a working backend prototype with API, persistence,
upload validation, confidence review logic, batch-job scaffolding,
matching, and a match-suggestion review workflow.

The following major capstone requirements remain incomplete or
not demonstrated:
- Genuine image vision inference.
- Required 40-image and 10-post labeled corpus.
- Complete persisted image/post embedding lifecycle.
- Per-call AI cost tracking and budget enforcement.
- Full behavioral verification using the required real dataset.

Do not interpret a passing automated test suite as proof that these
remaining requirements have been completed.
