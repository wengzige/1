import json
import re
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class DraftResult:
    media_id: str


@dataclass
class ImagePostResult:
    media_id: str
    image_count: int


_FORBIDDEN_SCAFFOLD_MARKERS = (
    "公众号草稿模板",
    "模板说明",
    "把准备好的正文 HTML 放在这里",
    "如果要自动上传正文图片并替换成微信地址",
    "兼容提醒",
)


def _has_suspicious_mojibake(text: str) -> bool:
    consecutive = 0
    total = 0
    for ch in text:
        codepoint = ord(ch)
        if 0x0080 <= codepoint <= 0x00FF:
            consecutive += 1
            total += 1
            if consecutive >= 3 or total >= 6:
                return True
        else:
            consecutive = 0
    return False


def _assert_clean_publish_payload(title: str, digest: str, html: str) -> None:
    """Block obviously dirty or garbled content before publishing."""
    joined = "\n".join(part for part in (title, digest, html) if part)

    if "\ufffd" in joined:
        raise ValueError("Publish blocked: replacement character U+FFFD detected in payload")

    if "<!--" in html:
        raise ValueError("Publish blocked: HTML comments detected in payload")

    if re.search(r"\?{3,}", joined):
        raise ValueError(
            "Publish blocked: suspicious garbled text detected (three or more consecutive question marks)"
        )

    if _has_suspicious_mojibake(joined):
        raise ValueError("Publish blocked: suspicious mojibake text detected (broken encoding pattern)")

    for marker in _FORBIDDEN_SCAFFOLD_MARKERS:
        if marker in joined:
            raise ValueError(f"Publish blocked: template scaffolding text detected: {marker}")


def _post_json(
    *,
    url: str,
    access_token: str,
    body: dict,
    error_prefix: str,
) -> dict:
    resp = requests.post(
        url,
        params={"access_token": access_token},
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )

    data = resp.json()
    errcode = data.get("errcode", 0)
    if errcode != 0:
        errmsg = data.get("errmsg", "unknown error")
        raise ValueError(f"WeChat {error_prefix} error: errcode={errcode}, errmsg={errmsg}")

    return data


def create_draft_from_payload(access_token: str, body: dict) -> DraftResult:
    """
    Create a draft in WeChat from a prebuilt /cgi-bin/draft/add payload.
    """
    articles = body.get("articles") or []
    for article in articles:
        if not isinstance(article, dict):
            raise ValueError("WeChat create_draft error: each article payload must be an object")
        _assert_clean_publish_payload(
            title=str(article.get("title") or ""),
            digest=str(article.get("digest") or ""),
            html=str(article.get("content") or ""),
        )

    data = _post_json(
        url="https://api.weixin.qq.com/cgi-bin/draft/add",
        access_token=access_token,
        body=body,
        error_prefix="create_draft",
    )

    if "media_id" not in data:
        raise ValueError(f"WeChat create_draft error: missing media_id in response: {data}")

    return DraftResult(media_id=data["media_id"])


def create_draft(
    access_token: str,
    title: str,
    html: str,
    digest: str,
    thumb_media_id: Optional[str] = None,
    author: Optional[str] = None,
) -> DraftResult:
    """
    Create a draft in WeChat.
    API: POST https://api.weixin.qq.com/cgi-bin/draft/add
    Returns DraftResult.
    Raise ValueError on error.
    """
    article = {
        "title": title,
        "author": author or "",
        "digest": digest,
        "content": html,
        "show_cover_pic": 0,
    }

    if thumb_media_id:
        article["thumb_media_id"] = thumb_media_id

    body = {"articles": [article]}
    return create_draft_from_payload(access_token=access_token, body=body)


def update_draft(
    access_token: str,
    media_id: str,
    article: dict,
    index: int = 0,
) -> DraftResult:
    """
    Update an existing draft in WeChat.
    API: POST https://api.weixin.qq.com/cgi-bin/draft/update
    Returns DraftResult with the same media_id on success.
    """
    if not media_id:
        raise ValueError("WeChat update_draft error: media_id is required")
    if not isinstance(article, dict):
        raise ValueError("WeChat update_draft error: article payload must be an object")

    _assert_clean_publish_payload(
        title=str(article.get("title") or ""),
        digest=str(article.get("digest") or ""),
        html=str(article.get("content") or ""),
    )

    body = {
        "media_id": media_id,
        "index": index,
        "articles": article,
    }

    _post_json(
        url="https://api.weixin.qq.com/cgi-bin/draft/update",
        access_token=access_token,
        body=body,
        error_prefix="update_draft",
    )

    return DraftResult(media_id=media_id)


def create_image_post(
    access_token: str,
    title: str,
    image_media_ids: list[str],
    content: str = "",
    open_comment: bool = False,
    fans_only_comment: bool = False,
) -> ImagePostResult:
    """
    Create a WeChat image post draft using article_type="newspic".
    """
    if not image_media_ids:
        raise ValueError("At least 1 image is required for image post")
    if len(image_media_ids) > 20:
        raise ValueError(f"Max 20 images allowed, got {len(image_media_ids)}")
    if len(title) > 32:
        raise ValueError(f"Title max 32 chars for image post, got {len(title)}")

    article = {
        "article_type": "newspic",
        "title": title,
        "content": content,
        "image_info": {
            "image_list": [{"image_media_id": mid} for mid in image_media_ids]
        },
        "need_open_comment": 1 if open_comment else 0,
        "only_fans_can_comment": 1 if fans_only_comment else 0,
    }

    body = {"articles": [article]}
    data = _post_json(
        url="https://api.weixin.qq.com/cgi-bin/draft/add",
        access_token=access_token,
        body=body,
        error_prefix="create_image_post",
    )

    if "media_id" not in data:
        raise ValueError(f"WeChat create_image_post error: missing media_id in response: {data}")

    return ImagePostResult(
        media_id=data["media_id"],
        image_count=len(image_media_ids),
    )
