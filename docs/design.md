# Image Relevance & Auto-Tagging — Design

## Problem

Build a backend service that understands an image library, automatically assigns structured metadata, and matches images to relevant blog posts using semantic similarity. The system must reject incorrect or low-confidence matches rather than return a misleading recommendation.

## Scope

- Process at least 40 licensed-free images across four or more categories.
- Generate and validate structured image metadata.
- Store image and post embeddings and rank candidates by semantic similarity.
- Implement a mismatch guard using tags, confidence, and evaluation-tuned thresholds.
- Run image processing and embedding generation as background jobs with retries.
- Track AI processing costs and expose endpoints for reviewing, approving, and rejecting suggestions.
- Evaluate top-1 precision using at least 10 labeled posts.

## Architecture

FastAPI routes → services and mismatch guard → repositories → PostgreSQL.

Background jobs handle image understanding, embedding generation, retries, and cost logging. A review API exposes suggested matches and their explanations.

## Data model

Core entities: images, tags and metadata, embeddings, posts, suggestions, approvals/rejections, and processing/cost records.

## API surface

- Health check.
- Image ingestion and batch processing.
- Post creation and image-match retrieval.
- Suggestion review, approval, and rejection.
- Evaluation and processing-status inspection.

Exact routes will be finalized during implementation.

## Reliability and safety

Validate all incoming requests and model output. Flag low-confidence metadata, retry transient processing failures, track costs per AI call, and reject mismatches with human-readable reasons. Return no confident match when no candidate passes the guard.

## Non-goal

Building a public image-hosting platform or a full-featured frontend is outside the MVP.

## Evaluation

Use a labeled set of at least 10 posts to measure top-1 precision. Include tests proving that a red-fox post prefers a fox image, rejects a wolf candidate, and returns no confident match when appropriate.

## Limitations

Matching quality depends on the metadata and embedding models, the chosen thresholds, and the size and coverage of the evaluation dataset. Mocked vision responses, if necessary, must be documented honestly.