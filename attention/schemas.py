from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "attention.v1"
ProviderName = Literal["auto", "gemini", "minimax"]


class ImageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str | None = None
    base64: str | None = None
    mime_type: str | None = None

    @model_validator(mode="after")
    def validate_source(self):
        has_path = bool((self.path or "").strip())
        has_base64 = bool((self.base64 or "").strip())
        if has_path == has_base64:
            raise ValueError("image.path 与 image.base64 必须二选一。")
        if has_base64 and not str(self.mime_type or "").strip():
            raise ValueError("使用 image.base64 时必须提供 mime_type。")
        return self


class AttentionError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    suggestions: list[str] = Field(default_factory=list)


class ResponseMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_requested: ProviderName
    provider_used: str = ""
    warnings: list[str] = Field(default_factory=list)
    used_viral_research: bool | None = None
    source_images: list[str] = Field(default_factory=list)
    failed_images: list[str] = Field(default_factory=list)
    photos_analyzed: int | None = None


class IntentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hero_element: str
    hero_reason: str = ""
    supporting_elements: list[str] = Field(default_factory=list)
    mood: str = ""
    viewer_question: str
    attention_angle: str = ""
    social_search_query: str = ""
    info_needed: list[str] = Field(default_factory=list)
    relevance_score: float | int | None = None


class CopyCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title_a: str = ""
    title_b: str = ""
    content: str = ""
    tags: str = ""


class AnalyzeImageIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    image: ImageInput
    provider: ProviderName = "auto"
    api_key: str = ""


class AnalyzeImageIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    status: Literal["ok", "error"]
    intent: IntentPayload | None = None
    meta: ResponseMeta
    error: AttentionError | None = None


class ContextSubject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    source: str = ""
    price: str = ""
    notes: str = ""


class ContextScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: str = ""
    time: str = ""
    feeling: str = ""


class CopyContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: ContextSubject = Field(default_factory=ContextSubject)
    supporting: list[str] = Field(default_factory=list)
    scene: ContextScene = Field(default_factory=ContextScene)
    extra: str = ""


class GenerateAttentionCopyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    intent: IntentPayload
    context: CopyContext = Field(default_factory=CopyContext)
    provider: ProviderName = "auto"
    api_key: str = ""
    include_viral_research: bool = True


class GenerateAttentionCopyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    status: Literal["ok", "error"]
    intent: IntentPayload | None = None
    copy_candidates: list[CopyCandidate] = Field(default_factory=list)
    best_copy: CopyCandidate | None = None
    why_it_works: str = ""
    markdown: str = ""
    meta: ResponseMeta
    error: AttentionError | None = None
