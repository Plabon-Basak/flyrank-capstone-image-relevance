DEFAULT_CONFIDENCE_THRESHOLD = 0.70


def requires_review(
    confidence: float,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> bool:
    return confidence < threshold
