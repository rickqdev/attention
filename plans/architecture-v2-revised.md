# Attention v2 Revised Architecture

## Product Reframe

FROM: "AI-native content creator agent for Chinese social platforms (full pipeline, agent architecture)"
TO: **Open-source AI Chinese social media copywriting engine. Photos in, platform-ready copy out.**

Not an agent. Not a social media management platform. A focused content generation library with CLI/API/MCP surfaces.

---

## Why This Change

The original v2 plan conflates three products:

| Product | Original Stages | Reality |
|---------|----------------|---------|
| Copy engine | Analyze + Research + Generate | Core value, unique, defensible |
| Publishing tool | Publish + Browser | Fragile, legal risk, commodity |
| Analytics platform | Monitor + Monetize + UGC + Stage | Different user, different product |

The copy engine is what nobody else does well. Publishing and analytics are what bigger teams (Postiz, native platform tools) do better.

---

## Architecture

### Package Structure (v2 revised)

```
attention/
  attention/
    __init__.py
    schemas.py           # v1 Pydantic models (keep, proven)
    config.py            # Config loading (keep, proven)
    errors.py            # Error types (keep, proven)
    pipeline.py          # 4-step pipeline (simplify from 7)

    steps/               # RENAME from agents/ -- these are not agents
      __init__.py
      base.py            # StepBase (rename from AgentStep)
      ingest.py          # [1] Image + context loading (KEEP as-is)
      analyze.py         # [2] Vision analysis (KEEP as-is)
      research.py        # [3] Hotspot + viral research (KEEP as-is)
      generate.py        # [4] Copy generation (KEEP as-is)

    providers/
      __init__.py
      base.py            # LLMProvider + ProviderChain (KEEP)
      gemini.py          # Primary: vision + text (KEEP)
      openai_compat.py   # NEW: OpenAI-compatible (replaces minimax+glm+ollama)

    format/              # NEW: pure text formatting, no publishing
      __init__.py
      xiaohongshu.py     # XHS format rules (title 20 chars, content 1000, tags 30)
      douyin.py          # Douyin format rules
      weibo.py           # Weibo format rules
      generic.py         # Fallback (no platform constraints)

    core.py              # REWRITE: use v2 pipeline, drop v1 delegation
    cli.py               # KEEP
    api.py               # KEEP + add v2 endpoints
    mcp_server.py        # KEEP + add pipeline tool

  modules/               # DEPRECATE: keep for backward compat, mark deprecated
    base.py
    photo_tagger.py
    copywriter.py
    context_loader.py

  app.py                 # Gradio UI (KEEP)
  pyproject.toml
```

### What Gets Cut

| Module | Action | Reason |
|--------|--------|--------|
| `agents/review.py` | REMOVE from pipeline | Review is a UI/caller concern, not a pipeline stage. Callers (CLI/API/Gradio) handle approval in their own way. |
| `platforms/` | DELETE directory | Publishing is not our product. Format rules move to `format/`. |
| `browser/` | DELETE directory | No browser automation. Users publish manually or use other tools. |
| `storage/stage.py` | DELETE | Account lifecycle is MCN tooling, not copy generation. |
| `tools/monetize.py` | DELETE | Different product. |
| `tools/analytics.py` | DELETE | Different product. |
| `tools/hotspot.py` | MERGE into `steps/research.py` | Already duplicated. Single source of truth. |
| `providers/minimax.py` | DELETE | Covered by openai_compat.py (MiniMax uses OpenAI-compatible API) |
| `providers/glm.py` | DELETE | Covered by openai_compat.py (GLM uses OpenAI-compatible API) |
| `providers/ollama.py` | DELETE | Covered by openai_compat.py (Ollama uses OpenAI-compatible API) |

### What Gets Added

| Module | Purpose |
|--------|---------|
| `providers/openai_compat.py` | One provider covering ANY OpenAI-compatible API (MiniMax, GLM, Ollama, DeepSeek, Qwen, etc.) User provides base_url + api_key + model. |
| `format/` directory | Pure formatting: given raw copy, apply platform-specific constraints (char limits, tag rules, image count). No network calls, no auth, no browser. |
| Pipeline wiring in `core.py` | Currently missing. `core.py` should construct `Pipeline([IngestStep(), AnalyzeStep(chain), ResearchStep(chain), GenerateStep(chain)])` and run it. |

---

## Pipeline (4 stages, down from 7)

```
[1] Ingest     Load images + context from directory/paths
      |
[2] Analyze    Vision analysis: hero element, mood, viewer question
      |
[3] Research   (optional) Hotspot trends + viral pattern extraction
      |
[4] Generate   Copy generation: title A/B, content, tags
      |
  -> Output    PipelineState with copy_candidates, best_copy, formatted per platform
```

Stage 5 (Review), 6 (Publish), 7 (Monitor) are removed from the pipeline.

Review is the caller's responsibility:
- CLI: prompt user before saving
- API: return result, caller decides
- MCP: return to Claude, user decides
- Gradio: show preview with edit/approve buttons

Format (platform adaptation) runs as a post-processing step on the output, not as a pipeline stage.

---

## Provider Strategy

Two providers cover 95%+ of use cases:

### 1. Gemini (Primary)
- Vision + text
- Free tier generous
- Best for Chinese content (multilingual training data)
- Already fully implemented

### 2. OpenAI-Compatible (Universal Fallback)
- Single implementation covers: OpenAI, DeepSeek, Qwen (cloud), MiniMax, GLM, Ollama, vLLM, LM Studio, any OpenAI-compatible endpoint
- User provides: `base_url`, `api_key`, `model`
- Optional: `supports_vision` flag (defaults to false)
- This replaces 3 separate provider files with 1

### ProviderChain
- Keep the fallback chain pattern
- Default: Gemini -> OpenAI-compatible
- User can configure order and params per provider

---

## Format Layer (replaces Platform Adapters)

Platform formatting is pure text transformation, not a network/publishing concern:

```python
class PlatformFormatter:
    """Format copy output for a specific platform."""
    name: str
    max_title: int
    max_content: int
    max_tags: int
    max_images: int

    def format(self, copy: CopyCandidate, images: list[str]) -> FormattedPost:
        """Apply platform constraints. Truncate, reformat, validate."""
        ...

    def validate(self, post: FormattedPost) -> list[str]:
        """Return list of warnings (too long, too many tags, etc.)."""
        ...
```

This is dramatically simpler than `PlatformAdapter` which tried to handle auth, sessions, publishing, comments, and analytics.

---

## Naming Changes

| Old | New | Reason |
|-----|-----|--------|
| `agents/` | `steps/` | These are pipeline steps, not autonomous agents |
| `AgentStep` | `Step` (or `PipelineStep`) | Accuracy |
| `platforms/` | `format/` | We format, we don't publish |
| `PlatformAdapter` | `PlatformFormatter` | Formatting, not adapting to an API |
| `PipelineState.review_status` | Remove | Not our concern |
| `PipelineState.publish_results` | Remove | Not our concern |
| `PipelineState.analytics` | Remove | Not our concern |
| `PipelineState.monetization` | Remove | Not our concern |

---

## PipelineState (Simplified)

```python
class PipelineState(BaseModel):
    schema_version: str = "attention.v2"

    # Input
    images: list[str] = []
    extra_context: str = ""
    target_platforms: list[str] = ["xiaohongshu"]  # for formatting

    # Stage 2: Analyze
    intent: IntentPayload | None = None
    analyzed_images: list[dict] = []

    # Stage 3: Research (optional)
    research: ResearchPayload | None = None

    # Stage 4: Generate
    copy_candidates: list[CopyCandidate] = []
    best_copy: CopyCandidate | None = None
    why_it_works: str = ""

    # Post-pipeline: Format
    formatted: dict[str, FormattedPost] = {}  # platform -> formatted output

    # Metadata
    pipeline_id: str
    created_at: datetime
    steps_completed: list[str] = []
    warnings: list[str] = []
    provider_used: str = ""

    # Config overrides
    provider: str = "auto"
    api_key: str = ""
    include_viral_research: bool = True
```

Fields removed: `review_status`, `review_feedback`, `platform_posts`, `publish_results`, `analytics`, `monetization`, `auto_approve`, `tavily_api_key` (move to config).

---

## Migration: v1 -> v2

### Phase 1: Consolidate (current task)
1. Rename `agents/` -> `steps/`, rename class
2. Delete: `platforms/`, `browser/`, `storage/`, `tools/monetize.py`, `tools/analytics.py`
3. Merge `tools/hotspot.py` into `steps/research.py`
4. Create `providers/openai_compat.py`, delete minimax/glm/ollama
5. Create `format/` with pure formatters
6. Rewrite `core.py` to use v2 pipeline (drop v1 delegation)
7. Simplify `PipelineState` (remove publish/monitor/review fields)
8. Add pipeline wiring (construct + run the 4-step pipeline)

### Phase 2: Polish
1. Async refactor (urllib -> httpx) for providers
2. Tests for pipeline + each step + formatters
3. Update CLI/API/MCP to use v2 pipeline
4. Deprecation warnings on v1 `modules/`

### Phase 3: Ship
1. README rewrite (focused positioning)
2. Gradio UI update
3. PyPI publish as 2.0.0
4. examples/ with real use cases

---

## Competitive Narrative (Revised)

Old: "We do everything Postiz does but for Chinese platforms"
New: "We do one thing nobody else does well"

> **Attention** turns your photos into ready-to-post Chinese social media copy.
>
> Upload photos. Get XHS/Douyin/Weibo-optimized titles, content, and tags.
> With optional trending topic research to make your copy timely.
>
> Not a publishing tool. Not an analytics dashboard. Just the best AI copywriter for Chinese social media.

vs Postiz: They manage your accounts. We write your copy.
vs social-push: They publish for you. We create for you.
vs ChatGPT: It doesn't see your photos, doesn't know XHS culture, doesn't track today's trending topics.

---

## Open Questions

1. **MCP as primary surface?** Claude/Cursor users are the most natural audience for a developer library. Should MCP be promoted above CLI?

2. **Gradio vs Web UI?** Gradio is fast to ship but limits customization. For non-developer users, a simple web page (Vercel deploy) might be better long-term.

3. **License**: Currently MIT. Plan says Apache-2.0. Pick one. Apache-2.0 is fine for a library (patent grant is a plus).

4. **Version**: Jump to 2.0.0 with the restructure, or keep 1.x and call this a refactor?
