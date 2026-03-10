#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description="Run one local attention HTTP demo flow.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000", help="Local attention API base URL")
    parser.add_argument("--image", required=True, help="Path to a local image")
    parser.add_argument("--provider", default="gemini", choices=["auto", "gemini", "minimax"])
    parser.add_argument("--api-key", required=True, help="Runtime provider API key")
    parser.add_argument("--extra", default="", help="Optional extra context")
    args = parser.parse_args()

    image_path = str(Path(args.image).expanduser().resolve())
    intent_resp = httpx.post(
        f"{args.api_base.rstrip('/')}/v1/intent/analyze",
        json={
            "schema_version": "attention.v1",
            "image": {"path": image_path},
            "provider": args.provider,
            "api_key": args.api_key,
        },
        timeout=60,
    )
    intent_payload = intent_resp.json()
    print("# intent")
    print(json.dumps(intent_payload, ensure_ascii=False, indent=2))
    if intent_payload.get("status") != "ok":
        return 1

    copy_resp = httpx.post(
        f"{args.api_base.rstrip('/')}/v1/copy/generate",
        json={
            "schema_version": "attention.v1",
            "intent": intent_payload["intent"],
            "context": {
                "subject": {"name": "", "source": "", "price": "", "notes": ""},
                "supporting": [],
                "scene": {"location": "", "time": "", "feeling": ""},
                "extra": args.extra,
            },
            "provider": args.provider,
            "api_key": args.api_key,
            "include_viral_research": False,
            "tavily_api_key": "",
        },
        timeout=60,
    )
    copy_payload = copy_resp.json()
    print("# copy")
    print(json.dumps(copy_payload, ensure_ascii=False, indent=2))
    return 0 if copy_payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
