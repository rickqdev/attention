from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .core import analyze_image_intent, generate_attention_copy
from .schemas import AnalyzeImageIntentRequest, GenerateAttentionCopyRequest

mcp = FastMCP(
    name="attention",
    instructions=(
        "Use analyze_image_intent first to extract the visual hook from an image, "
        "then use generate_attention_copy to turn that intent into Chinese copy."
    ),
)


@mcp.tool(
    name="analyze_image_intent",
    description="Analyze one image and return the strongest attention angle as structured JSON.",
)
def analyze_image_intent_tool(image: dict, provider: str = "auto", api_key: str = "") -> dict:
    request = AnalyzeImageIntentRequest(
        image=image,
        provider=provider,
        api_key=api_key,
    )
    return analyze_image_intent(request).model_dump(exclude_none=True)


@mcp.tool(
    name="generate_attention_copy",
    description="Generate Chinese social copy from a verified image intent and optional context.",
)
def generate_attention_copy_tool(
    intent: dict,
    context: dict | None = None,
    provider: str = "auto",
    api_key: str = "",
    include_viral_research: bool = False,
    tavily_api_key: str = "",
) -> dict:
    request = GenerateAttentionCopyRequest(
        intent=intent,
        context=context or {},
        provider=provider,
        api_key=api_key,
        include_viral_research=include_viral_research,
        tavily_api_key=tavily_api_key,
    )
    return generate_attention_copy(request).model_dump(exclude_none=True)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
