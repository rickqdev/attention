"""Stage 2.5: Arrange -- 9-grid photo curation from analyzed batch.

Replaces SelectStep. Picks best 9 photos, assigns cover + grid positions,
enforces diversity rules, and produces a narrative arrangement.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from .base import Step

logger = logging.getLogger("attention.steps.arrange")

DEFAULT_GRID_SIZE = 9

# Cover hard thresholds
COVER_IMPACT_MIN = 7.0
COVER_EMOTION_MIN = 6.0

# Diversity caps
MAX_SAME_HERO = 2
MAX_SAME_MOOD = 3

# Grid position roles
SLOT_ROLES = {
    1: "视觉钩子",
    2: "核心支撑",
    3: "核心支撑",
    4: "细节展开",
    5: "细节展开",
    6: "细节展开",
    7: "情感收束",
    8: "情感收束",
    9: "行动锚点",
}


def _pick_cover(candidates: list[dict]) -> dict:
    """Pick the best cover image. Requires impact >= 7 and emotion >= 6."""
    qualified = [
        img for img in candidates
        if img.get("visual_impact", 0) >= COVER_IMPACT_MIN
        and img.get("emotion_pull", 0) >= COVER_EMOTION_MIN
    ]
    pool = qualified if qualified else candidates
    return max(pool, key=lambda x: x.get("cover_potential", 0))


def _cover_alternatives(candidates: list[dict], cover: dict) -> list[dict]:
    """Return close runner-ups for cover (within 1 point of cover_potential)."""
    threshold = cover.get("cover_potential", 0) - 1.0
    return [
        img for img in candidates
        if img is not cover
        and img.get("cover_potential", 0) >= threshold
    ][:2]


def _deduplicate(images: list[dict]) -> list[dict]:
    """Enforce diversity: cap same hero_element and same mood."""
    hero_count: Counter = Counter()
    mood_count: Counter = Counter()
    kept: list[dict] = []

    for img in images:
        hero = img.get("hero_element", "")
        mood = img.get("mood", "")

        if hero and hero_count[hero] >= MAX_SAME_HERO:
            continue
        if mood and mood_count[mood] >= MAX_SAME_MOOD:
            continue

        hero_count[hero] += 1
        mood_count[mood] += 1
        kept.append(img)

    return kept


def _has_action_info(img: dict) -> bool:
    """Check if image has actionable info (price, location, purchase cues)."""
    elements = " ".join(img.get("all_elements", []))
    info = " ".join(img.get("info_needed", []))
    action_keywords = ["价格", "地址", "店", "购买", "链接", "菜单", "价", "元", "¥", "￥"]
    text = elements + " " + info + " " + img.get("hero_element", "")
    return any(kw in text for kw in action_keywords)


def _assign_slots(cover: dict, remaining: list[dict], grid_size: int) -> list[dict]:
    """Assign images to grid positions 2-N based on role logic."""
    slots = [{"position": 1, "image": cover, "role": SLOT_ROLES[1]}]

    if not remaining:
        return slots

    need = min(grid_size - 1, len(remaining))

    # Sort pools for each role
    by_composite = sorted(remaining, key=lambda x: x.get("composite_score", 0), reverse=True)
    by_info = sorted(remaining, key=lambda x: x.get("info_density", 0), reverse=True)
    by_emotion = sorted(remaining, key=lambda x: x.get("emotion_pull", 0), reverse=True)

    used = {cover.get("filename")}
    assigned: list[dict] = []

    def pick_from(pool: list[dict]) -> dict | None:
        for img in pool:
            if img.get("filename") not in used:
                used.add(img.get("filename"))
                return img
        return None

    # Positions 2-3: core support (highest composite)
    for pos in range(2, min(4, need + 2)):
        img = pick_from(by_composite)
        if img:
            assigned.append({"position": pos, "image": img, "role": SLOT_ROLES.get(pos, "补充")})

    # Positions 4-6: detail (highest info_density)
    for pos in range(4, min(7, need + 2)):
        if len(assigned) >= need:
            break
        img = pick_from(by_info)
        if img:
            assigned.append({"position": pos, "image": img, "role": SLOT_ROLES.get(pos, "补充")})

    # Positions 7-8: emotional closure (highest emotion_pull)
    for pos in range(7, min(9, need + 2)):
        if len(assigned) >= need:
            break
        img = pick_from(by_emotion)
        if img:
            assigned.append({"position": pos, "image": img, "role": SLOT_ROLES.get(pos, "补充")})

    # Position 9: action anchor (has price/location info, or highest composite of remaining)
    if len(assigned) < need:
        action_candidates = [img for img in remaining if img.get("filename") not in used and _has_action_info(img)]
        img = action_candidates[0] if action_candidates else pick_from(by_composite)
        if img:
            assigned.append({"position": len(assigned) + 2, "image": img, "role": SLOT_ROLES.get(9, "行动锚点")})

    # Fill any remaining slots
    while len(assigned) < need:
        img = pick_from(by_composite)
        if not img:
            break
        assigned.append({"position": len(assigned) + 2, "image": img, "role": "补充"})

    slots.extend(assigned)
    return slots


def _build_narrative(slots: list[dict]) -> str:
    """Generate a one-sentence grid narrative from assigned slots."""
    if not slots:
        return ""

    parts = []
    cover_hero = slots[0]["image"].get("hero_element", "主角")
    parts.append(f"封面用{cover_hero}制造视觉钩子")

    detail_heroes = [
        s["image"].get("hero_element", "")
        for s in slots if s["role"] == "细节展开" and s["image"].get("hero_element")
    ]
    if detail_heroes:
        parts.append(f"中段展开{'、'.join(detail_heroes[:2])}的细节")

    emotion_moods = [
        s["image"].get("mood", "")
        for s in slots if s["role"] == "情感收束" and s["image"].get("mood")
    ]
    if emotion_moods:
        parts.append(f"收尾用{emotion_moods[0]}做情感锚定")

    return " → ".join(parts)


class ArrangeStep(Step):
    name = "arrange"

    def __init__(self, grid_size: int = DEFAULT_GRID_SIZE):
        self.grid_size = grid_size

    async def run(self, state):
        from attention.schemas import GridSlot, GridResult, IntentPayload

        if not state.analyzed_images:
            state.warnings.append("No analyzed images to arrange")
            return state

        total = len(state.analyzed_images)

        # Sort by composite_score descending
        ranked = sorted(
            state.analyzed_images,
            key=lambda x: x.get("composite_score", 0),
            reverse=True,
        )

        # Deduplicate
        diverse = _deduplicate(ranked)

        # Pick cover
        cover = _pick_cover(diverse)
        cover_alts = _cover_alternatives(diverse, cover)

        # Remaining candidates (excluding cover)
        remaining = [img for img in diverse if img is not cover]

        # Assign grid positions
        raw_slots = _assign_slots(cover, remaining, self.grid_size)

        # Build GridSlot objects
        grid_slots = []
        for slot in raw_slots:
            img = slot["image"]
            grid_slots.append(GridSlot(
                position=slot["position"],
                filename=img.get("filename", ""),
                role=slot["role"],
                composite_score=img.get("composite_score", 0),
                cover_potential=img.get("cover_potential", 0),
                reason=img.get("hero_reason", img.get("attention_angle", "")),
            ))

        # Excluded images
        selected_filenames = {s.filename for s in grid_slots}
        excluded_images = [img for img in state.analyzed_images if img.get("filename") not in selected_filenames]

        # Build grid result
        narrative = _build_narrative(raw_slots)
        state.grid = GridResult(
            cover=grid_slots[0] if grid_slots else None,
            cover_alternatives=[
                GridSlot(
                    position=0,
                    filename=alt.get("filename", ""),
                    role="封面备选",
                    composite_score=alt.get("composite_score", 0),
                    cover_potential=alt.get("cover_potential", 0),
                    reason=alt.get("hero_reason", ""),
                )
                for alt in cover_alts
            ],
            slots=grid_slots,
            excluded=[
                {"filename": img.get("filename", ""), "composite_score": img.get("composite_score", 0),
                 "exclude_reason": img.get("exclude_reason") or "未入选九宫格"}
                for img in excluded_images
            ],
            grid_narrative=narrative,
        )

        # Update state: keep only selected images in analyzed_images
        state.analyzed_images = [
            img for img in state.analyzed_images
            if img.get("filename") in selected_filenames
        ]

        # Update intent to cover image
        state.intent = IntentPayload(
            hero_element=str(cover.get("hero_element", "")).strip(),
            hero_reason=str(cover.get("hero_reason", "")).strip(),
            supporting_elements=[
                str(s).strip()
                for s in cover.get("supporting_elements", [])
                if str(s).strip()
            ],
            mood=str(cover.get("mood", "")).strip(),
            viewer_question=str(cover.get("viewer_question", "")).strip(),
            attention_angle=str(cover.get("attention_angle", "")).strip(),
            social_search_query=str(cover.get("social_search_query", "")).strip(),
            info_needed=[
                str(s).strip()
                for s in cover.get("info_needed", [])
                if str(s).strip()
            ],
            relevance_score=cover.get("relevance_score"),
        )

        # Update image paths
        if state.images:
            state.images = [
                p for p in state.images if Path(p).name in selected_filenames
            ]

        if total < 4:
            state.warnings.append(f"只有 {total} 张图，不足以组九宫格，建议补拍")

        logger.info(
            "Arranged %d/%d photos into grid (cover: %s, score: %.1f)",
            len(grid_slots), total,
            cover.get("filename", "?"),
            cover.get("composite_score", 0),
        )
        return state
