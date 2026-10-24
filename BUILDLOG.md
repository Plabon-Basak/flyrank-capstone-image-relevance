# AI Development Build Log

## Project

**Project:** Image Relevance & Auto-Tagging Engine
**Repository:** Plabon-Basak/flyrank-capstone-image-relevance
**Stack:** Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic, pytest

## AI Assistance

AI assistance was used as a development support tool throughout the project.

Areas where AI helped:

1. **Project planning**
   - Breaking the capstone requirements into smaller implementation stages.
   - Identifying backend components and API workflows.

2. **Backend development support**
   - Explaining FastAPI routes, Pydantic schemas, SQLAlchemy models, database migrations, and service-layer responsibilities.
   - Helping investigate implementation errors and test failures.

3. **Testing and debugging**
   - Reviewing pytest output and identifying relevant test cases.
   - Helping troubleshoot PostgreSQL configuration, image uploads, batch processing, and API behavior.
   - Reviewing matching and confidence-threshold behavior.

4. **Documentation**
   - Helping structure README.md, capstone.yaml, EVIDENCE.md, and this build log.
   - Comparing implemented features with the original capstone requirements.

## Human Verification and Decisions

The project was developed and tested locally.

Development decisions included:

- PostgreSQL was used for persistent application data.
- Alembic was used for database schema migrations.
- Image uploads use file validation and configured size limits.
- Confidence values below the configured threshold require review.
- A lexical matching baseline was retained for local matching.
- Mock metadata was not accepted as genuine image analysis.
- Match suggestions support pending, approved, and rejected states.

Implementation changes were checked against the local project, API behavior, or automated tests where applicable.

## Incorrect Assumptions and Corrections

1. **Mock metadata versus image understanding**

   A valid mock metadata response is not evidence that a vision model analyzed image pixels. The batch processor deliberately rejects mock metadata as real image analysis. Documentation was updated to state this limitation.

2. **Lexical matching versus semantic understanding**

   Token-based lexical matching is not equivalent to neural semantic image embeddings. The README describes the lexical baseline and the limitations of the optional text-embedding provider.

3. **Synthetic evaluation versus real-world performance**

   The ten-case synthetic evaluation is a development baseline. Its results do not demonstrate performance on the required real image and blog-post dataset.

4. **Passing tests versus complete capstone compliance**

   Automated tests verify specific implemented behaviors. They do not prove that every capstone requirement is complete. EVIDENCE.md distinguishes verified, partially implemented, and unimplemented work.

## Current Verification

The following results were observed during development:

- 84 automated tests were collected and previously passed.
- PostgreSQL connection and Alembic migrations were verified.
- Image upload and validation tests passed.
- Batch-job and retry behavior were tested.
- Matching and mismatch-guard behavior were tested.
- Match-suggestion review workflow was manually exercised.
- A synthetic evaluation script was created with ten labeled cases.

Run the test suite again before submission:

```powershell
python -m pytest -q
## Remaining Work

The following requirements are not yet fully implemented or demonstrated:

- Genuine vision-model inference.
- At least 40 images across four or more categories.
- At least 10 blog posts with labeled correct image associations.
- Complete persisted image and post embedding lifecycle.
- Per-call vision and embedding cost tracking.
- Budget enforcement and full operational monitoring.
- Automated tests dedicated to the match-suggestion review API.

## Development Responsibility

AI assistance supported planning, troubleshooting, implementation guidance, testing, and documentation. The developer remains responsible for understanding, reviewing, verifying, and explaining the submitted implementation and its limitations.
