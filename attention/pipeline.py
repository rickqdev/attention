"""Pipeline orchestrator for the 4-step attention pipeline.

Steps: Ingest -> Analyze -> Research -> Generate
Each step receives and returns a PipelineState.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .schemas import CopyCandidate, GridResult, IntentPayload
from .steps.base import Step

logger = logging.getLogger("attention.pipeline")


class ResearchPayload(BaseModel):
    """Hotspot and competitor research data."""
    topics: list[str] = Field(default_factory=list)
    sources: dict[str, int] = Field(default_factory=dict)
    competitor_insight: str = ""
    viral_insights: dict[str, Any] = Field(default_factory=dict)


class PipelineState(BaseModel):
    """State passed through the pipeline."""

    schema_version: str = "attention.v2"

    # Input
    photos_dir: str = ""
    images: list[str] = Field(default_factory=list)
    extra_context: str = ""
    target_platforms: list[str] = Field(default_factory=lambda: ["xiaohongshu"])

    # Stage 2: Analyze
    intent: IntentPayload | None = None
    analyzed_images: list[dict[str, Any]] = Field(default_factory=list)

    # Stage 2.5: Arrange (grid)
    grid: GridResult | None = None

    # Stage 3: Research (optional)
    research: ResearchPayload | None = None

    # Stage 4: Generate
    copy_candidates: list[CopyCandidate] = Field(default_factory=list)
    best_copy: CopyCandidate | None = None
    why_it_works: str = ""

    # Metadata
    pipeline_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    steps_completed: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provider_used: str = ""

    # Config overrides
    provider: str = "auto"
    api_key: str = ""
    include_viral_research: bool = True


class Pipeline:
    """Orchestrator that runs steps in sequence."""

    def __init__(self, steps: list[Step]):
        self.steps = steps

    async def run(self, state: PipelineState) -> PipelineState:
        for step in self.steps:
            if step.should_skip(state):
                logger.info("Skipping step: %s", step.name)
                continue
            logger.info("Running step: %s", step.name)
            try:
                state = await step.run(state)
                state.steps_completed.append(step.name)
            except Exception as exc:
                logger.error("Step %s failed: %s", step.name, exc)
                state.warnings.append(f"Step {step.name} failed: {str(exc)[:200]}")
                raise
        return state

    async def run_until(self, state: PipelineState, stop_after: str) -> PipelineState:
        """Run pipeline but stop after a specific step name."""
        for step in self.steps:
            if step.should_skip(state):
                continue
            state = await step.run(state)
            state.steps_completed.append(step.name)
            if step.name == stop_after:
                break
        return state


def run_sync(pipeline: Pipeline, state: PipelineState) -> PipelineState:
    """Synchronous wrapper for running a pipeline."""
    return asyncio.run(pipeline.run(state))
