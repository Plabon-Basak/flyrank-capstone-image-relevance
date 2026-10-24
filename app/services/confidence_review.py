DEFAULT_CONFIDENCE_THRESHOLD = 0.70


def requires_review(
    confidence: float,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> bool:
    return confidence < threshold


def requires_match_review(
    confidence: float | None,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> bool:
    if confidence is None:
        return True
    return confidence < threshold
