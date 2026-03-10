#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Encode a local image into attention API compatible Base64 JSON.")
    parser.add_argument("image", help="Absolute or relative path to the image file")
    args = parser.parse_args()

    path = Path(args.image).expanduser().resolve()
    mime_type, _ = mimetypes.guess_type(path.name)
    payload = {
        "base64": base64.b64encode(path.read_bytes()).decode("utf-8"),
        "mime_type": mime_type or "image/jpeg",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
