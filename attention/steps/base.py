"""Base class for pipeline steps."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attention.pipeline import PipelineState


class Step(ABC):
    """A single step in the attention pipeline.

    Each step receives the current PipelineState, performs its work,
    and returns an updated PipelineState.
    """

    name: str = "unnamed"

    @abstractmethod
    async def run(self, state: PipelineState) -> PipelineState:
        """Execute this step and return updated state."""
        ...

    def should_skip(self, state: PipelineState) -> bool:
        """Override to conditionally skip this step."""
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
