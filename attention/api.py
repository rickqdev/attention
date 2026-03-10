from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from .core import analyze_image_intent, generate_attention_copy
from .schemas import AnalyzeImageIntentRequest, GenerateAttentionCopyRequest

app = FastAPI(
    title="attention API",
    version="1.0.0",
    description="HTTP API for attention / 注意力. BYOK by default.",
)


@app.get("/healthz")
def healthcheck():
    return {"status": "ok", "service": "attention-api"}


@app.post("/v1/intent/analyze")
def analyze_intent_endpoint(payload: AnalyzeImageIntentRequest):
    return analyze_image_intent(payload).model_dump(exclude_none=True)


@app.post("/v1/copy/generate")
def generate_copy_endpoint(payload: GenerateAttentionCopyRequest):
    return generate_attention_copy(payload).model_dump(exclude_none=True)


def main():
    uvicorn.run("attention.api:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
