# Capstone Evidence

This document maps the current implementation to the Image Relevance & Auto-Tagging Engine capstone requirements.

Statuses reflect evidence actually observed during development. A passing unit test does not independently establish production readiness, real-world accuracy, or complete capstone compliance.

## 1. Structured Metadata and Genuine Vision Analysis

**Status: Partially verified — provider integration demonstrated**

Implementation:
- Gemini Vision integration for image analysis.
- Structured metadata extraction.
- Subject, category, attributes, caption, and confidence fields.
- Metadata schema validation.
- Confidence-based review logic.

Evidence:
- `app/services/metadata_provider.py`
- `tests/test_metadata_provider.py`
- `tests/test_image_schema.py`
- `tests/test_images_api.py`

Manual integration evidence:

A real image analysis request was performed using:

`POST /images/3/analyze`

The provider returned:

- Subject: Nivea Men Fresh Active roll-on deodorant.
- Category: Personal Care.
- Confidence: 0.98.
- Structured attributes and a generated caption.
- Provider: Gemini.

Limitation:

This demonstrates successful analysis for one test image. It does not establish accuracy across a diverse image dataset.

## 2. Low-Confidence Review

**Status: Verified for implemented threshold logic**

Evidence:
- `app/services/confidence_review.py`
- `tests/test_confidence_review.py`
- `tests/test_images_api.py`

The default review boundary is 0.70:

- Confidence below 0.70 requires review.
- Confidence at or above 0.70 does not require review under the tested configuration.

Boundary cases include 0.45, 0.69, 0.70, and 0.96.

## 3. Batch Processing and Retries

**Status: Partially verified**

Implementation:
- Batch-job creation and retrieval.
- Progress and failure tracking.
- Retry behavior.
- Provider-aware processing.

Evidence:
- `app/services/batch_processor.py`
- `tests/test_batch_jobs_api.py`
- `tests/test_batch_job_model.py`
- `tests/test_batch_processor.py`

Relevant tests:
- `test_process_batch_job_success`
- `test_process_batch_job_retries_missing_file`
- `test_process_batch_job_rejects_mock_metadata`

Limitation:

Batch-job behavior and retry handling are tested. A successful batch run using genuine Gemini Vision analysis across the required 40-image corpus has not been demonstrated.

## 4. Per-Call Vision and Embedding Cost Tracking
**Status: Partially implemented**

The project provides per-call cost calculation, reservation with budget checks, and persistence via `api_usage`. Vision and embedding requests are tracked in API paths; batch processing and backfill do not yet participate fully in tracked cost accounting.

Outstanding work:

- Extend tracking to batch processing and backfill workflows.
- Add usage/cost inspection endpoints.
- Expand budget-enforcement coverage and tests.

## 5. Image and Blog-Post Embeddings

**Status: Partially verified — persistent text-embedding pipeline implemented**

Implementation:
- Gemini Embedding provider.
- Model: `gemini-embedding-001`.
- Vector dimensions: 768.
- Text generation from image metadata and captions.
- Text generation from blog-post content.
- Persistent embedding fields in PostgreSQL.
- Backfill script for existing records.

Evidence:
- `app/services/embedding_provider.py`
- `app/services/embedding_factory.py`
- `app/services/gemini_embedding_provider.py`
- `app/services/embedding_text.py`
- `app/models/image.py`
- `app/models/blog_post.py`
- `migrations/versions/10f26b25f0e9_add_persistent_embeddings.py`
- `scripts/backfill_embeddings.py`

Manual verification:
- Gemini embedding generation succeeded.
- Image and blog-post vectors were generated.
- Backfill saved one image embedding and one blog-post embedding.
- Database inspection confirmed 768-dimensional persisted vectors.
- Alembic reported migration `10f26b25f0e9` as the current head.

Important limitation:

These are text embeddings derived from image metadata and blog-post text. They are not direct embeddings of image pixels.

The complete lifecycle still needs validation against the required dataset.

## 6. Semantic Matching and Ranked Suggestions

**Status: Partially verified — implementation operational, relevance quality not established**

Implementation:
- Persistent embedding lookup.
- Semantic similarity calculation.
- Ranked blog-post suggestions.
- Similarity threshold and no-match behavior.
- Lexical baseline retained as an alternative.

Evidence:
- `app/services/matching_service.py`
- `app/services/embedding_text.py`
- `tests/test_matching_service.py`

Manual API verification:

`GET /images/3/matches`

returned a semantic match with similarity 0.663954.

However, the analyzed image was a Nivea deodorant product and the matched article concerned red foxes.

This is a likely false positive and demonstrates why similarity scores cannot be treated as proof of relevance.

Outstanding work:
- Evaluate a representative labeled dataset.
- Calibrate the similarity threshold.
- Improve false-positive rejection.
- Report precision and recall on the required corpus.

## 7. Mismatch Guard

**Status: Verified for specific tested cases**

Evidence:
- `app/services/matching_service.py`
- `tests/test_matching_service.py`
- `test_match_rejects_explicit_wolf_fox_mismatch`

Limitation:

The existing test verifies a specific wolf/fox mismatch. It does not establish comprehensive mismatch detection across all categories or subjects.

Additional probes are required for broader coverage.

## 8. No-Confident-Match Behavior

**Status: Verified for tested threshold behavior**

Evidence:
- `tests/test_matching_service.py`
- `test_match_returns_no_match_below_threshold`
- `test_match_handles_no_blog_posts`

The matching service returns no match when no candidate meets the configured threshold or when no candidate blog posts exist.

The threshold still requires calibration against real labeled data.

## 9. Database Models, Relationships, and Migrations

**Status: Partially verified**

Implemented persistence includes:
- Images.
- Blog posts.
- Batch jobs.
- Match suggestions.
- Persistent image embeddings.
- Persistent blog-post embeddings.

Evidence:
- `app/models/`
- `migrations/versions/`
- `tests/test_database_config.py`
- `tests/test_batch_job_model.py`

Manual verification:
- PostgreSQL connection succeeded.
- Alembic migration applied successfully.
- Current migration head: `10f26b25f0e9`.
- Embedding fields were verified in the database.

Limitation:

This evidence does not independently verify every relationship, index, constraint, or database requirement in the complete capstone specification.

## 10. API and Human Review Workflow

**Status: Implemented and manually exercised; automated coverage incomplete**

Implemented routes include:

- `GET /images`
- `GET /images/{image_id}`
- `POST /images`
- `POST /images/upload`
- `POST /images/{image_id}/analyze`
- `GET /images/{image_id}/matches`
- `POST /blog-posts`
- `GET /blog-posts`
- `GET /blog-posts/{post_id}`
- `POST /batch-jobs`
- `GET /batch-jobs/{job_id}`
- `GET /match-suggestions`
- `POST /match-suggestions/{suggestion_id}/review`

The review workflow supports:
- Pending suggestions.
- Approval.
- Rejection.
- Optional decision reasons.
- Filtering by review status.
- Protection against reviewing an already-reviewed suggestion.

Evidence:
- `app/services/match_suggestion_service.py`
- `tests/`
- Manual API testing through FastAPI Swagger documentation.

Limitation:

The review workflow has been manually exercised, but dedicated automated tests covering listing, filtering, approval, rejection, and duplicate-review protection should be added.

## 11. Labeled Evaluation Dataset

**Status: Incomplete**

Existing evidence:
- `scripts/evaluate.py` (synthetic, text-only lexical baseline)
- Ten manually labeled synthetic evaluation cases.
- Development baseline metrics documented in README.md:
  - Top-1 precision: 7/10 = 70.0%.
  - Accepted matches: 5/10 = 50.0%.
  - Precision among accepted matches: 5/5 = 100.0%.

Limitation:

These figures describe a synthetic, text-only lexical baseline only. They do not evaluate real image files, Gemini embeddings, API endpoints, database persistence, or the full pipeline. They are not production accuracy measurements and do not establish performance on the required real dataset.

Outstanding dataset requirements:
- At least 40 images.
- At least four categories.
- At least 10 blog posts.
- Labeled correct image-to-post associations.
- Reproducible evaluation using the actual matching pipeline.

## 12. Automated Test Suite

**Status: Verified for the current recorded test run**

Latest recorded result:

```text
105 passed, 1 warning in 9.39s
```

Additional verification:
- `python -m compileall -q app scripts` completed successfully.
- `git diff --check` completed without whitespace errors.

The warning concerns a dependency deprecation and did not prevent the test suite from passing.

Automated tests do not replace external-provider integration tests or real-dataset evaluation.

## 13. Documentation and Submission Files

**Status: Present; final review required**

Project documentation:
- `README.md`
- `BUILDLOG.md`
- `EVIDENCE.md`
- `capstone.yaml`
- `.env.example`

The README describes architecture, setup, API routes, provider configuration, matching behavior, testing, and known limitations.

Final submission review should ensure that all documentation agrees with the actual implementation and that no secrets or local environment files are committed.

## Behavioral Probe Summary

| Probe | Current evidence | Status |
|---|---|---|
| Genuine vision metadata extraction | Gemini Vision manually tested on one image | Partially verified |
| Batch processing with real vision metadata | Batch behavior tested; required real corpus not demonstrated | Partial |
| Red fox ranks above wolf and dog | Specific mismatch test exists; full ranking not established | Partial |
| Wolf candidate rejected for fox | `test_match_rejects_explicit_wolf_fox_mismatch` | Verified for this case |
| No suitable image returns no match | No-match threshold tests | Verified for tested cases |
| Persistent embeddings | 768-dimensional image metadata and blog-post text embeddings verified in PostgreSQL | Verified for tested records |
| Semantic relevance quality | A likely false positive was observed in live matching | Not established |
| Evaluation reproduces synthetic metrics | `scripts/evaluate.py` and ten synthetic cases | Development baseline |
| Every AI call has cost attribution | Partially implemented; batch and backfill not fully tracked | Partial |

## Final Assessment

The project is a functioning backend prototype with:

- FastAPI APIs.
- PostgreSQL persistence and Alembic migrations.
- Image upload and validation.
- Gemini Vision metadata extraction.
- Gemini text-embedding integration.
- Persistent 768-dimensional embeddings.
- Ranked matching and mismatch-guard logic.
- Batch-job scaffolding and retries.
- Match-suggestion review workflow.
- Automated tests.

The following major capstone requirements remain incomplete or insufficiently demonstrated:

1. Required labeled dataset of at least 40 images across four categories and at least 10 blog posts.
2. Reliable matching quality demonstrated through real-dataset evaluation using the actual pipeline.
3. Broader false-positive and behavioral probe validation.
4. Full batch processing verification on the required corpus.
5. Complete cost tracking coverage (batch and backfill) and usage inspection endpoints.
6. Broader budget enforcement coverage.

The current implementation should be described as an operational prototype, not a fully validated production-ready image-matching system.

**Dataset licensing/provenance:** Development/test placeholder images from Lorem Picsum endpoints. Individual original URLs and photographer identities not recorded; individual licenses not verified. Not public domain/openly licensed/copyright-free. See data/eval/manifest.json for details.
