#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLKIT_ROOT = REPO_ROOT / "toolkit"

if str(TOOLKIT_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLKIT_ROOT))

from publisher import create_draft_from_payload, update_draft  # noqa: E402
from wechat_api import get_access_token  # noqa: E402


CONFIG_PATHS = [
    Path.cwd() / "config.yaml",
    REPO_ROOT / "config.yaml",
    TOOLKIT_ROOT / "config.yaml",
    Path.home() / ".config" / "wewrite" / "config.yaml",
]


def load_config() -> dict:
    for path in CONFIG_PATHS:
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
    return {}


def load_payload(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("draft payload must be a JSON object")
    articles = data.get("articles")
    if not isinstance(articles, list) or not articles:
        raise ValueError("draft payload must contain a non-empty articles array")
    return data


def emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update a WeChat draft from a JSON payload.")
    parser.add_argument("--draft-json", required=True, help="Path to the generated draft.json payload")
    parser.add_argument("--media-id", default="", help="Existing draft media_id; when provided the draft is updated")
    parser.add_argument("--index", type=int, default=0, help="Article index to update inside an existing draft")
    parser.add_argument("--json", action="store_true", help="Reserved for compatibility with JSON-first callers")
    args = parser.parse_args()

    try:
        config = load_config()
        wechat_cfg = config.get("wechat", {}) if isinstance(config, dict) else {}
        appid = str(wechat_cfg.get("appid") or "").strip()
        secret = str(wechat_cfg.get("secret") or "").strip()
        if not appid or not secret:
            raise ValueError("wechat.appid or wechat.secret missing in config.yaml")

        draft_json_path = Path(args.draft_json).resolve()
        payload = load_payload(draft_json_path)
        token = get_access_token(appid, secret)

        media_id = str(args.media_id or "").strip()
        if media_id:
            articles = payload.get("articles") or []
            if len(articles) != 1:
                raise ValueError("draft/update currently requires exactly one article payload")
            result = update_draft(
                access_token=token,
                media_id=media_id,
                article=articles[0],
                index=args.index,
            )
            action = "updated"
        else:
            result = create_draft_from_payload(access_token=token, body=payload)
            action = "created"

        emit(
            {
                "success": True,
                "action": action,
                "media_id": result.media_id,
                "draft_json": str(draft_json_path),
                "index": args.index,
            }
        )
        return 0
    except Exception as exc:
        emit(
            {
                "success": False,
                "error": str(exc),
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
