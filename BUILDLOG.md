# AI Development Build Log

## Project

- **Project:** Image Relevance & Auto-Tagging Engine
- **Repository:** `Plabon-Basak/flyrank-capstone-image-relevance`
- **Stack:** Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Gemini, pytest
- **Development environment:** Windows, Python 3.14.2 virtual environment

## AI Assistance

AI assistance was used as a development support tool throughout the project.

Areas where AI helped:

1. **Project planning**
   - Breaking capstone requirements into manageable implementation stages.
   - Identifying backend components, API workflows, and service responsibilities.

2. **Backend development**
   - Explaining FastAPI routes, Pydantic schemas, SQLAlchemy models, database migrations, and service-layer architecture.
   - Supporting implementation of image uploads, metadata extraction, matching, batch processing, and review workflows.

3. **AI integration**
   - Supporting integration of Gemini Vision for image metadata extraction.
   - Supporting integration of Gemini Embedding for text embeddings.
   - Reviewing embedding persistence, backfill logic, and semantic similarity calculations.

4. **Testing and debugging**
   - Investigating implementation errors and test failures.
   - Reviewing pytest output and API behavior.
   - Troubleshooting PostgreSQL configuration, image storage, batch processing, and matching behavior.

5. **Documentation**
   - Supporting the preparation and review of README.md, EVIDENCE.md, capstone.yaml, and this build log.

## Implementation Progress

### Backend and persistence

- Implemented FastAPI application and API routes.
- Configured PostgreSQL database connectivity.
- Implemented SQLAlchemy models and Alembic migrations.
- Implemented image upload and file validation.
- Added image and blog-post metadata persistence.
- Implemented batch-job records and processing status tracking.
- Implemented persistent image and blog-post embedding fields.

### Image analysis

- Integrated Gemini Vision for actual image analysis.
- Configured the vision model through environment settings.
- Implemented structured metadata extraction, including subject, category, attributes, caption, and confidence.
- Retained metadata validation and confidence-based review logic.

A successful integration test analyzed an uploaded Nivea Men Fresh Active roll-on image and returned structured product metadata with confidence 0.98.

This demonstrates successful provider integration for that test image. It does not establish accuracy across the required evaluation dataset.

### Embedding and semantic matching

- Integrated Gemini Embedding using `gemini-embedding-001`.
- Configured 768-dimensional text embeddings.
- Generated embeddings from image metadata and captions.
- Generated embeddings from blog-post content.
- Added PostgreSQL persistence for generated vectors.
- Added a backfill script for existing records.
- Updated matching logic to use persistent embeddings when the configured provider supports them.
- Retained the lexical baseline as an alternative matching approach.

**Important implementation distinction:** The embedding provider generates text embeddings from extracted image metadata and blog content. It does not directly generate image-pixel embeddings.

A live matching request returned a semantic similarity score of 0.663954 for a deodorant image and a red-fox article. This was a likely false positive. Therefore, the integration is operational, but matching relevance and threshold calibration still require substantial evaluation.

### Matching and review workflow

- Implemented ranked blog-post suggestions.
- Implemented mismatch-guard logic for tested subject mismatches.
- Implemented no-confident-match behavior.
- Persisted match suggestions.
- Added pending, approved, and rejected review states.
- Added review-status filtering and duplicate-review protection.

### Batch processing

- Implemented batch-job creation and retrieval.
- Added progress and failure tracking.
- Implemented retry behavior.
- Updated batch processing to support the configured metadata and embedding providers.

A successful batch run across the required real-world dataset has not yet been demonstrated.

## Database and Migration Verification

The following were verified:

- PostgreSQL connection.
- Alembic migration execution.
- Current migration head: `10f26b25f0e9`.
- Persistent embedding columns for image and blog-post records.
- Existing image and blog-post embeddings stored as 768-dimensional vectors.

The embedding backfill script successfully processed the available records.

Observed backfill output:

- Image embeddings created: 1
- Blog-post embeddings created: 1
- Records skipped: 2

## Testing and Verification

Latest recorded automated test result:

```text
87 passed, 1 warning in 17.22s
```

Additional checks:

- `python -m compileall -q app scripts` completed successfully.
- `git diff --check` completed without whitespace errors.
- PostgreSQL connection and migration state were checked.
- Gemini Vision integration was manually exercised.
- Gemini Embedding generation was manually exercised.
- Embedding persistence and backfill were verified.
- Semantic matching endpoint was manually exercised.
- Match-suggestion review workflow was manually exercised.

The remaining LF-to-CRLF messages from Git are line-ending warnings, not whitespace errors.

## Incorrect Assumptions and Corrections

1. **Mock metadata versus genuine vision inference**

   Mock metadata is useful for isolated testing but does not constitute image understanding. Gemini Vision was subsequently integrated and manually verified.

2. **Lexical matching versus semantic matching**

   Lexical token similarity and neural text embeddings are different approaches. The project now supports Gemini text embeddings, while retaining the lexical baseline.

3. **Text embeddings versus image embeddings**

   The current embedding pipeline embeds text derived from image metadata and captions. It should not be described as a direct image-pixel embedding model.

4. **Similarity score versus relevance quality**

   A high similarity score does not guarantee a correct association. A live test produced a likely false positive between a deodorant image and a red-fox article. Real evaluation is required before claiming matching accuracy.

5. **Synthetic evaluation versus real-world performance**

   The ten-case synthetic evaluation is a development baseline, not proof of performance on the required real dataset.

6. **Passing tests versus complete capstone compliance**

   Automated tests verify implemented behavior. They do not prove completion of every dataset, cost, evaluation, or production requirement.

## Remaining Work

The following requirements remain incomplete or not fully demonstrated:

- Build a labeled corpus containing at least 40 images across at least four categories.
- Prepare at least 10 blog posts with labeled correct image associations.
- Evaluate matching quality using the required real dataset.
- Improve false-positive handling and calibrate the semantic similarity threshold.
- Demonstrate batch processing with genuine vision metadata across the required corpus.
- Implement per-call vision and embedding cost tracking.
- Implement budget enforcement.
- Expand behavioral probes and automated review-workflow coverage.
- Perform final end-to-end verification and submission review.

## Development Responsibility

AI assistance supported planning, implementation guidance, troubleshooting, testing, and documentation. The developer remains responsible for reviewing, understanding, verifying, and explaining the submitted implementation and its limitations.