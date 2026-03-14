"""Stage 2.5: Select -- Pick best photos from analyzed batch.

Sorts analyzed images by relevance_score and selects top N.
Inserted between Analyze and Research in the pipeline.
"""

from __future__ import annotations

import logging

from .base import Step

logger = logging.getLogger("attention.steps.select")

DEFAULT_MAX_SELECT = 9


class SelectStep(Step):
    name = "select"

    def __init__(self, max_select: int = DEFAULT_MAX_SELECT):
        self.max_select = max_select

    async def run(self, state):
        from attention.schemas import IntentPayload

        if not state.analyzed_images:
            state.warnings.append("No analyzed images to select from")
            return state

        total = len(state.analyzed_images)

        # Sort by relevance_score descending
        ranked = sorted(
            state.analyzed_images,
            key=lambda x: x.get("relevance_score", 0),
            reverse=True,
        )

        # Select top N
        selected = ranked[: self.max_select]
        excluded = ranked[self.max_select :]

        state.analyzed_images = selected

        # Update intent to best selected image
        best = selected[0]
        state.intent = IntentPayload(
            hero_element=str(best.get("hero_element", "")).strip(),
            hero_reason=str(best.get("hero_reason", "")).strip(),
            supporting_elements=[
                str(s).strip()
                for s in best.get("supporting_elements", [])
                if str(s).strip()
            ],
            mood=str(best.get("mood", "")).strip(),
            viewer_question=str(best.get("viewer_question", "")).strip(),
            attention_angle=str(best.get("attention_angle", "")).strip(),
            social_search_query=str(best.get("social_search_query", "")).strip(),
            info_needed=[
                str(s).strip()
                for s in best.get("info_needed", [])
                if str(s).strip()
            ],
            relevance_score=best.get("relevance_score"),
        )

        # Update image paths to match selected only
        selected_filenames = {img.get("filename") for img in selected if img.get("filename")}
        if selected_filenames and state.images:
            from pathlib import Path

            state.images = [
                p for p in state.images if Path(p).name in selected_filenames
            ]

        if excluded:
            excluded_names = [e.get("filename", "?") for e in excluded]
            state.warnings.append(
                f"Excluded {len(excluded)} low-relevance photos: {', '.join(excluded_names)}"
            )

        logger.info(
            "Selected %d/%d photos (top relevance scores: %s)",
            len(selected),
            total,
            [round(s.get("relevance_score", 0), 1) for s in selected[:3]],
        )
        return state
