from __future__ import annotations

import argparse

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


def build_parser():
    parser = argparse.ArgumentParser(description="Run the attention HTTP API server.")
    parser.add_argument("--host", default="127.0.0.1", help="API 监听地址，默认 127.0.0.1。")
    parser.add_argument("--port", type=int, default=8000, help="API 端口，默认 8000。")
    return parser


def main():
    args = build_parser().parse_args()
    uvicorn.run("attention.api:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
