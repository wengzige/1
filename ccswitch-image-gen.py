#!/usr/bin/env python3
import argparse
import base64
import mimetypes
import os
import secrets
from pathlib import Path
import json
import urllib.error
import urllib.request


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36"


def _read_prompt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _require_env() -> tuple[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is missing")
    if not base_url:
        raise SystemExit("OPENAI_BASE_URL is missing")
    return api_key, base_url.rstrip("/")


def _decode_first_image(result: dict, output: str) -> None:
    image_b64 = result["data"][0]["b64_json"]
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(image_b64))
    print(output_path)


def _request_json(url: str, api_key: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    return _open_json(request)


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _multipart_body(fields: list[tuple[str, str]], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = "----ccswitch-imagegen-" + secrets.token_hex(16)
    chunks: list[bytes] = []

    for name, value in fields:
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    for name, path in files:
        if not path.exists():
            raise SystemExit(f"Image file not found: {path}")
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode()
        )
        chunks.append(f"Content-Type: {_guess_mime(path)}\r\n\r\n".encode())
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def _request_multipart(url: str, api_key: str, fields: list[tuple[str, str]], files: list[tuple[str, Path]]) -> dict:
    body, boundary = _multipart_body(fields, files)
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    return _open_json(request)


def _open_json(request: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {error.code}: {body}") from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--size", default="1024x1536")
    parser.add_argument("--quality", default="high")
    parser.add_argument(
        "--image",
        action="append",
        help="Input/reference image path. Repeat for multiple images. When present, uses /images/edits.",
    )
    parser.add_argument("--mask", help="Optional PNG mask for edit requests.")
    args = parser.parse_args()

    api_key, base_url = _require_env()
    prompt = _read_prompt(args.prompt_file)

    if args.image:
        fields = [
            ("model", args.model),
            ("prompt", prompt),
            ("size", args.size),
            ("quality", args.quality),
        ]
        files = [("image", Path(path)) for path in args.image]
        if args.mask:
            files.append(("mask", Path(args.mask)))
        result = _request_multipart(base_url + "/images/edits", api_key, fields, files)
    else:
        result = _request_json(
            base_url + "/images/generations",
            api_key,
            {
                "model": args.model,
                "prompt": prompt,
                "size": args.size,
                "quality": args.quality,
            },
        )

    _decode_first_image(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
