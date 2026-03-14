# Attention v2 Architecture Upgrade Plan

## Positioning

**From**: image-to-copy CLI tool (single-step, 6 modules)
**To**: AI-native content creator agent for Chinese social platforms (full pipeline, agent architecture)

One-liner: **The open-source AI agent that turns your photos into published social media posts -- built for Xiaohongshu, Douyin, Weibo.**

GitHub tagline: `AI-powered content creation & publishing agent for Chinese social platforms. Image analysis -> copy generation -> scheduling -> publishing -> analytics.`

---

## Architecture: Agent Pipeline (borrowed from LangChain social-media-agent + Postiz)

### Core Pipeline (7-stage DAG)

```
[1] Ingest         Image/URL/text input + context loading
      |
[2] Analyze        Vision analysis (hero element, viewer question, mood)
      |
[3] Research       Hotspot trending (Weibo, Baidu, Tavily) + competitor analysis
      |
[4] Generate       AI copy generation (multi-variant A/B) + image optimization
      |
[5] Review         Human-in-the-loop: preview, edit, approve/reject
      |
[6] Publish        Multi-platform publishing (XHS, Douyin, Weibo, WeChat)
      |
[7] Monitor        Comment tracking, engagement analytics, growth reports
```

Each stage = independent module, can run standalone or chained.

### Package Structure (v2)

```
attention/
+-- pyproject.toml                    # Package config
+-- README.md                         # English (GitHub-facing)
+-- README.zh-CN.md                   # Chinese (user-facing)
+-- LICENSE                           # Apache-2.0
|
+-- attention/                        # Core library
|   +-- __init__.py
|   +-- schemas.py                    # Pydantic models (attention.v2 contract)
|   +-- config.py                     # Config loading, validation, defaults
|   +-- pipeline.py                   # Pipeline orchestrator (DAG runner)
|   +-- errors.py                     # Structured error types
|   |
|   +-- agents/                       # Agent pipeline stages
|   |   +-- __init__.py
|   |   +-- base.py                   # AgentStep abstract class
|   |   +-- ingest.py                 # [1] Input normalization
|   |   +-- analyze.py                # [2] Vision analysis (from photo_tagger)
|   |   +-- research.py              # [3] Hotspot + competitor research
|   |   +-- generate.py              # [4] Copy generation (from copywriter)
|   |   +-- review.py                # [5] HITL approval gate
|   |   +-- publish.py               # [6] Multi-platform publishing
|   |   +-- monitor.py               # [7] Engagement tracking
|   |
|   +-- platforms/                    # Platform adapters (borrowed from Postiz pattern)
|   |   +-- __init__.py
|   |   +-- base.py                   # PlatformAdapter abstract class
|   |   +-- xiaohongshu.py           # XHS: publish, comments, analytics
|   |   +-- douyin.py                # Douyin: video/image posting
|   |   +-- weibo.py                 # Weibo: microblog posting
|   |   +-- wechat.py                # WeChat Official Account
|   |   +-- twitter.py               # X/Twitter (international reach)
|   |
|   +-- providers/                    # LLM provider abstraction
|   |   +-- __init__.py
|   |   +-- base.py                   # LLMProvider abstract class
|   |   +-- gemini.py                # Google Gemini (primary)
|   |   +-- openai.py                # OpenAI/compatible (user BYO)
|   |   +-- ollama.py                # Local models
|   |   +-- minimax.py               # MiniMax
|   |   +-- glm.py                   # Zhipu GLM
|   |
|   +-- tools/                        # Composable tools (monetization, analytics)
|   |   +-- __init__.py
|   |   +-- hotspot.py               # Trending topic tracker
|   |   +-- monetize.py              # Keyword analysis, product recs, media kit
|   |   +-- ugc.py                   # Brand collaboration matching
|   |   +-- analytics.py             # Growth tracking, weekly reports
|   |   +-- pdf.py                   # Style guide export
|   |   +-- notify.py                # Multi-channel notifications
|   |
|   +-- browser/                      # Browser automation layer
|   |   +-- __init__.py
|   |   +-- engine.py                # Playwright wrapper with stealth
|   |   +-- session.py               # Cookie/auth session management
|   |   +-- adaptive.py              # AI-adaptive element discovery (from social-push)
|   |
|   +-- storage/                      # Data persistence
|       +-- __init__.py
|       +-- history.py               # Publish history, comment history
|       +-- stage.py                 # Account lifecycle state
|       +-- dedup.py                 # URL/content deduplication
|
+-- server/                           # Server entry points
|   +-- api.py                        # FastAPI HTTP server
|   +-- mcp.py                        # MCP server for Claude/LLM integration
|
+-- cli/                              # CLI entry points
|   +-- main.py                       # Main CLI (replaces old cli.py + main.py)
|   +-- schedule.py                   # Cron/scheduler daemon
|
+-- app.py                            # Gradio web demo (enhanced)
|
+-- workflows/                        # Platform workflow definitions (from social-push)
|   +-- xiaohongshu-image.md
|   +-- xiaohongshu-article.md
|   +-- douyin-video.md
|   +-- weibo-post.md
|   +-- wechat-article.md
|   +-- twitter-post.md
|
+-- examples/                         # Usage examples
|   +-- quickstart.py
|   +-- custom-pipeline.py
|   +-- add-platform.md
|
+-- docs/                             # Documentation
|   +-- architecture.md
|   +-- api-reference.md
|   +-- platforms.md
|   +-- contributing.md
|
+-- tests/                            # Test suite
    +-- test_pipeline.py
    +-- test_analyze.py
    +-- test_generate.py
    +-- test_platforms.py
```

---

## Key Architecture Decisions

### 1. Agent Step Pattern (from LangChain, simplified for Python)

```python
class AgentStep(ABC):
    """Base class for pipeline stages."""
    name: str

    @abstractmethod
    async def run(self, state: PipelineState) -> PipelineState:
        """Execute step, return updated state."""
        ...

    def should_skip(self, state: PipelineState) -> bool:
        """Override for conditional execution."""
        return False
```

Pipeline runner executes steps in DAG order, passing `PipelineState` between them.
Steps can be individually tested, swapped, or extended.

### 2. Platform Adapter Pattern (from Postiz SocialAbstract)

```python
class PlatformAdapter(ABC):
    name: str
    max_title_length: int
    max_content_length: int
    supported_media: list[str]  # ["image", "video", "carousel"]

    @abstractmethod
    async def publish(self, post: Post, session: Session) -> PublishResult: ...

    @abstractmethod
    async def fetch_comments(self, post_id: str, session: Session) -> list[Comment]: ...

    async def refresh_session(self, session: Session) -> Session: ...
```

Adding a new platform = implement one class + one workflow markdown file. No core changes.

### 3. Workflow Markdown (from social-push)

Each platform has a human-readable workflow definition:

```markdown
# Xiaohongshu Image Post

## Auth
- Cookie-based session (exported from browser)
- Session file: ~/.attention/sessions/xiaohongshu.json

## Steps
1. Navigate to creator.xiaohongshu.com/publish/publish
2. Upload images (max 9, aspect ratio 3:4 preferred)
3. Fill title (max 20 chars)
4. Fill content body
5. Add hashtags
6. Save as draft (default) or publish (if --auto-publish flag)

## Constraints
- Title: 20 chars max
- Content: 1000 chars max
- Images: 9 max, JPG/PNG
- Hashtags: 30 max
```

### 4. HITL Review Gate (from LangChain interrupt pattern)

```python
class ReviewStep(AgentStep):
    """Human-in-the-loop approval gate."""

    async def run(self, state: PipelineState) -> PipelineState:
        if state.auto_approve:
            return state

        # Present preview to user
        preview = self.format_preview(state)

        # Block until user responds
        response = await self.wait_for_review(preview)

        match response.action:
            case "approve": return state
            case "edit":    return self.apply_edits(state, response.edits)
            case "reject":  raise PipelineAborted("User rejected")
            case "retry":   return state.with_retry(response.feedback)
```

Review gate works across all entry points:
- CLI: interactive prompt
- API: webhook callback / polling endpoint
- MCP: tool response
- Gradio: UI buttons

### 5. Provider Abstraction (clean up current base.py)

```python
class LLMProvider(ABC):
    name: str
    supports_vision: bool

    @abstractmethod
    async def generate(self, prompt: str, images: list[bytes] | None = None,
                       temperature: float = 0.8) -> str: ...

class ProviderChain:
    """Auto-fallback across providers."""

    def __init__(self, providers: list[LLMProvider]):
        self.providers = providers

    async def generate(self, prompt, images=None, **kwargs):
        for provider in self.providers:
            if images and not provider.supports_vision:
                continue
            try:
                return await provider.generate(prompt, images, **kwargs)
            except ProviderError:
                continue
        raise AllProvidersFailedError()
```

### 6. Schema v2 (backward-compatible extension of v1)

```python
class PipelineState(BaseModel):
    schema_version: str = "attention.v2"

    # v1 fields (unchanged)
    intent: IntentPayload | None = None
    copy_candidates: list[CopyCandidate] = []
    best_copy: CopyCandidate | None = None

    # v2 additions
    research: ResearchPayload | None = None      # hotspot + competitor data
    platform_posts: dict[str, PlatformPost] = {} # per-platform formatted posts
    publish_results: dict[str, PublishResult] = {}
    review_status: ReviewStatus = ReviewStatus.PENDING
    monetization: MonetizationPayload | None = None
    analytics: AnalyticsPayload | None = None

    # Pipeline metadata
    pipeline_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    steps_completed: list[str] = []
```

---

## Feature Priority (v2.0 -> v2.1 -> v2.2)

### v2.0 - Foundation (open-source the extended modules)

1. Restructure to agent pipeline architecture
2. Open-source all Attention-post modules (hotspot, publisher, monetize, etc.)
3. Platform adapter: Xiaohongshu (image + article)
4. HITL review gate (CLI + API)
5. Provider abstraction (Gemini, OpenAI-compatible, Ollama)
6. Config system upgrade (YAML, env vars, validation)
7. Tests for core pipeline + analyze + generate

### v2.1 - Multi-Platform + Scheduling

1. Platform adapters: Douyin, Weibo, Twitter/X
2. Scheduling daemon (cron-based, APScheduler or Celery Beat)
3. Content calendar CLI (`attention calendar --week`)
4. Browser automation upgrade (Playwright stealth + adaptive refs)
5. Gradio UI v2 (dashboard with pipeline status, history, analytics)
6. Workflow markdown for all platforms

### v2.2 - Analytics + Growth

1. Engagement analytics dashboard
2. Account lifecycle management (stage gating)
3. UGC brand collaboration matching
4. Weekly AI-powered growth reports
5. Notification integrations (email, Feishu, Discord webhook)
6. PDF style guide export

---

## GitHub Growth Strategy

### README (English-first, Chinese toggle)

Structure (borrowed from Postiz/n8n top repos):

```
# attention

The open-source AI agent for Chinese social media content creation.

[one-line description]
[badges: stars, license, pypi, discord]
[hero screenshot / GIF demo]

## What it does
[3-bullet value prop]

## Quick Start
[pip install + 5-line code example]

## Platforms
[table: XHS, Douyin, Weibo, WeChat, Twitter -- with checkmarks]

## Architecture
[pipeline diagram]

## Contributing
[link to CONTRIBUTING.md]

## Star History
[star-history chart embed]
```

### Discoverability

Topics/tags:
- `social-media`, `xiaohongshu`, `content-creation`, `ai-agent`
- `chinese-social-media`, `douyin`, `weibo`, `social-media-automation`
- `content-scheduling`, `ai-copywriting`, `mcp-server`

### Community

1. GitHub Discussions (Q&A, feature requests, show & tell)
2. Discord server (real-time help, Chinese + English channels)
3. `examples/` with real use cases (fashion, food, travel, tech)
4. `CONTRIBUTING.md` with "add a platform" guide (lowest barrier to contribute)

### Launch

1. Post on: Hacker News, Reddit r/selfhosted + r/SideProject, V2EX, Product Hunt
2. Chinese channels: V2EX, Juejin, Zhihu, WeChat developer groups
3. Comparison table: attention vs Postiz vs social-push vs manual workflow

---

## Migration Path (current -> v2)

### Phase 1: Restructure (no new features, pure refactor)

1. Move `modules/photo_tagger.py` -> `attention/agents/analyze.py`
2. Move `modules/copywriter.py` -> `attention/agents/generate.py`
3. Move `modules/context_loader.py` -> `attention/agents/ingest.py`
4. Move `modules/base.py` -> split into `providers/` directory
5. Merge Attention-post modules into `attention/tools/` and `attention/platforms/`
6. Create `pipeline.py` orchestrator
7. Keep v1 API endpoints working (backward compat)
8. Add v2 endpoints alongside

### Phase 2: Platform adapters + HITL

1. Extract `publisher.py` logic into `platforms/xiaohongshu.py`
2. Add `ReviewStep` with CLI interactive mode
3. Add `PlatformAdapter` for XHS with workflow markdown
4. Tests

### Phase 3: Polish + Launch

1. Gradio UI v2
2. Documentation
3. Examples
4. README overhaul
5. PyPI publish
6. Launch campaign

---

## Technical Debt to Fix

1. **base.py is 400+ lines**: Split into provider-per-file
2. **No async**: All API calls are synchronous. Move to httpx async for parallel provider calls
3. **No tests**: Zero test coverage. Add pytest suite for core pipeline
4. **Config is fragile**: JSON-only, no validation, no defaults. Use pydantic Settings
5. **No deduplication**: Can generate same content for same image repeatedly. Add content hash store
6. **Error handling**: Mix of None returns and exceptions. Standardize on typed errors
7. **Logging**: Custom `log()` function. Replace with stdlib logging + structlog

---

## Competitive Moat

| vs Postiz (27K stars) | attention wins because |
|---|---|
| English-first, Western platforms | Chinese platforms native (XHS, Douyin, Weibo) |
| UI-heavy web app (Next.js + NestJS) | CLI-first + API + MCP (developer-friendly, composable) |
| Generic AI copilot | Vision-first: image analysis -> copy (unique) |
| No content research | Built-in hotspot + competitor analysis |
| AGPL license | Apache-2.0 (more permissive) |

| vs social-push (328 stars) | attention wins because |
|---|---|
| Publishing only (human writes content) | Full pipeline: analyze -> generate -> publish |
| Claude Code only | Multi-interface: CLI + API + MCP + Gradio |
| No analytics | Engagement tracking + growth reports |
| No monetization | Keyword analysis + brand matching + media kits |

| vs LangChain agent (2.4K stars) | attention wins because |
|---|---|
| LangGraph dependency (heavy) | Lightweight Python, no framework lock-in |
| English content only | Chinese social media native |
| Text-only input | Image-first input (vision analysis) |
| Complex setup (LangSmith, Arcade AI, etc.) | `pip install attention` + API key = running |
