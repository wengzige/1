#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import requests
import yaml
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict[str, Any]:
    config_path = REPO_ROOT / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml is not a mapping")
    return data


def get_access_token(appid: str, secret: str) -> str:
    resp = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ValueError(f"WeChat token error: {data}")
    return str(token)


def fetch_draft(access_token: str, media_id: str) -> dict[str, Any]:
    resp = requests.post(
        f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={access_token}",
        json={"media_id": media_id},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errcode"):
        raise ValueError(f"WeChat draft/get error: {data}")
    return data


def _maybe_fix_mojibake(text: str) -> str:
    if not text:
        return text
    suspicious = ("Ã", "Â", "ä", "å", "æ", "ç", "è", "é", "ï", "\x80", "\x99")
    if not any(token in text for token in suspicious):
        return text
    try:
        repaired = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        return text
    return repaired if repaired else text


def _repair_obj(value: Any) -> Any:
    if isinstance(value, str):
        return _maybe_fix_mojibake(value)
    if isinstance(value, list):
        return [_repair_obj(item) for item in value]
    if isinstance(value, dict):
        return {key: _repair_obj(item) for key, item in value.items()}
    return value


def _replace_tag_with_text(tag: Tag, text: str) -> None:
    tag.replace_with(NavigableString(text))


def html_to_markdownish(title: str, html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for br in soup.find_all("br"):
        br.replace_with(NavigableString("\n"))

    for img in soup.find_all("img"):
        alt = img.get("alt", "").strip() or "配图"
        src = (
            img.get("data-src", "").strip()
            or img.get("src", "").strip()
            or ""
        )
        _replace_tag_with_text(img, f"\n![{alt}]({src})\n")

    for em in soup.find_all("em"):
        text = em.get_text(" ", strip=True)
        _replace_tag_with_text(em, f"\n*{text}*\n" if text else "")

    for heading, prefix in (("h1", "# "), ("h2", "## "), ("h3", "### ")):
        for tag in soup.find_all(heading):
            text = tag.get_text(" ", strip=True)
            _replace_tag_with_text(tag, f"\n{prefix}{text}\n" if text else "")

    for span in soup.find_all("span"):
        span.unwrap()

    text = soup.get_text("\n")
    text = _maybe_fix_mojibake(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^(WARNING|INFO)\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    lines: list[str] = [f"# {title}"]
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if line in {title, f"# {title}"}:
            continue
        lines.append(line)

    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip() + "\n"
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a WeChat draft and save a markdownish local copy.")
    parser.add_argument("--media-id", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    config = load_config()
    wechat_cfg = config.get("wechat") or {}
    appid = str(wechat_cfg.get("appid") or "").strip()
    secret = str(wechat_cfg.get("secret") or "").strip()
    if not appid or not secret:
        raise ValueError("wechat.appid or wechat.secret missing in config.yaml")

    token = get_access_token(appid, secret)
    data = fetch_draft(token, args.media_id)
    repaired = _repair_obj(data)

    news_items = repaired.get("news_item") or repaired.get("articles") or []
    if not news_items:
        raise ValueError("draft/get returned no articles")
    article = news_items[0]
    title = str(article.get("title") or "").strip()
    html = str(article.get("content") or "")
    markdownish = html_to_markdownish(title, html)

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(repaired, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(markdownish, encoding="utf-8")

    print(
        json.dumps(
            {
                "media_id": args.media_id,
                "output_json": str(output_json),
                "output_md": str(output_md),
                "title": title,
                "update_time": repaired.get("update_time"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
