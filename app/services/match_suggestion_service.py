
from sqlalchemy.orm import Session

from app.models.match_suggestion import MatchSuggestion


def save_match_suggestions(
    db: Session,
    image_id: int,
    matches: list[dict],
) -> list[MatchSuggestion]:
    saved_suggestions = []

    try:
        for match in matches:
            blog_post_id = match["blog_post_id"]

            suggestion = (
                db.query(MatchSuggestion)
                .filter(
                    MatchSuggestion.image_id == image_id,
                    MatchSuggestion.blog_post_id == blog_post_id,
                )
                .first()
            )

            if suggestion is None:
                suggestion = MatchSuggestion(
                    image_id=image_id,
                    blog_post_id=blog_post_id,
                    similarity=match["similarity"],
                    matching_reason=match["reason"],
                    status="pending",
                )
                db.add(suggestion)
            elif suggestion.status == "pending":
                suggestion.similarity = match["similarity"]
                suggestion.matching_reason = match["reason"]

            saved_suggestions.append(suggestion)

        db.commit()

        for suggestion in saved_suggestions:
            db.refresh(suggestion)

        return saved_suggestions

    except Exception:
        db.rollback()
        raise
