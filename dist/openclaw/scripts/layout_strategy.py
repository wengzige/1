#!/usr/bin/env python3
"""Layout/theme selection and diversity checks for WeWrite articles."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


SKILL_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = SKILL_ROOT / "output"


LAYOUT_FAMILIES: dict[str, dict[str, Any]] = {
    "professional-info": {
        "variant": "info-flow",
        "themes": ["bytedance", "github", "professional-clean"],
        "keywords": [
            "行业",
            "商业",
            "公司",
            "平台",
            "市场",
            "监管",
            "治理",
            "数据",
            "报告",
            "外卖",
            "商标",
            "品牌",
        ],
        "patterns": [
            "scene>callout>table>image>quote",
            "data-lead>callout>timeline>image>decision",
            "contrast>comparison-table>warning>image>quote",
        ],
    },
    "tech-magazine": {
        "variant": "tech-magazine",
        "themes": ["tech-modern", "midnight", "bauhaus", "github"],
        "keywords": [
            "AI",
            "Agent",
            "模型",
            "开源",
            "API",
            "代码",
            "工具",
            "产品",
            "系统",
            "DeepSeek",
            "苹果",
            "芯片",
            "上下文",
        ],
        "patterns": [
            "dialogue>spec-card>timeline>image>quote",
            "scene>callout>architecture-image>warning>checklist",
            "data-lead>comparison-table>timeline>quote>action",
        ],
    },
    "editorial-commentary": {
        "variant": "editorial",
        "themes": ["sspai", "warm-editorial", "newspaper"],
        "keywords": [
            "观点",
            "评论",
            "观察",
            "人物",
            "争议",
            "为什么",
            "不是",
            "而是",
            "背后",
            "值得",
        ],
        "patterns": [
            "conflict>quote>argument>dialogue>image>open-question",
            "scene>callout>argument>quote>image>short-ending",
            "dialogue-lead>argument>warning>quote>image",
        ],
    },
    "focus-opinion": {
        "variant": "focus",
        "themes": ["focus-red", "bold-navy", "bold-green"],
        "keywords": [
            "快评",
            "强观点",
            "警惕",
            "风险",
            "危险",
            "不该",
            "必须",
            "真相",
            "乱象",
            "治理",
            "新闻",
        ],
        "patterns": [
            "conflict>quote>warning>argument>image>verdict",
            "data-lead>callout>three-claims>dialogue>quote",
            "scene>warning>timeline>image>hard-ending",
        ],
    },
    "minimal-essay": {
        "variant": "minimal",
        "themes": ["minimal", "minimal-gold", "ink"],
        "keywords": [
            "文化",
            "读书",
            "品牌",
            "长期",
            "慢内容",
            "审美",
            "生活",
            "人文",
            "留白",
        ],
        "patterns": [
            "quiet-scene>quote>short-sections>image>open-ending",
            "question>minimal-callout>contrast>quote>image",
            "scene>three-notes>image>quote>short-ending",
        ],
    },
    "lifestyle-emotion": {
        "variant": "warm",
        "themes": ["elegant-rose", "warm-editorial", "minimal-gold"],
        "keywords": [
            "女性",
            "消费",
            "生活方式",
            "健康",
            "过敏",
            "长寿",
            "情绪",
            "审美",
            "日常",
            "治愈",
        ],
        "patterns": [
            "scene>dialogue>callout>image>soft-ending",
            "personal-lead>warning>timeline>image>quote",
            "question>callout>three-scenes>quote>image",
        ],
    },
}


THEME_TO_FAMILY = {
    theme: family
    for family, config in LAYOUT_FAMILIES.items()
    for theme in config["themes"]
}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def extract_title(markdown_text: str, fallback: str = "") -> str:
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return fallback


def stable_index(seed: str, count: int) -> int:
    if count <= 0:
        return 0
    return sum(ord(ch) for ch in seed) % count


def rotated(items: list[str], seed: str) -> list[str]:
    if not items:
        return []
    idx = stable_index(seed, len(items))
    return items[idx:] + items[:idx]


def extract_module_sequence(markdown_text: str) -> list[str]:
    events: list[tuple[int, str]] = []

    for match in re.finditer(r":::(callout|timeline|dialogue|quote)\b", markdown_text):
        events.append((match.start(), match.group(1)))

    for match in re.finditer(r"!\[[^\]]*\]\([^)]+\)", markdown_text):
        events.append((match.start(), "image"))

    lines = markdown_text.splitlines(keepends=True)
    offset = 0
    for idx, line in enumerate(lines[:-1]):
        next_line = lines[idx + 1]
        if "|" in line and re.search(r"\|\s*:?-{3,}:?\s*\|", next_line):
            events.append((offset, "table"))
        offset += len(line)

    events.sort(key=lambda item: item[0])

    sequence: list[str] = []
    for _, kind in events:
        if not sequence or sequence[-1] != kind:
            sequence.append(kind)
    return sequence


def module_pattern(markdown_text: str) -> str:
    sequence = extract_module_sequence(markdown_text)
    return ">".join(sequence) if sequence else "plain"


def rank_layout_families(title: str, markdown_text: str) -> list[tuple[str, int]]:
    text = f"{title}\n{markdown_text[:5000]}"
    scores: list[tuple[str, int]] = []
    for family, config in LAYOUT_FAMILIES.items():
        score = 0
        for keyword in config["keywords"]:
            score += text.lower().count(str(keyword).lower())
        scores.append((family, score))

    if all(score == 0 for _, score in scores):
        scores = [
            ("professional-info", 1),
            ("editorial-commentary", 1),
            ("tech-magazine", 1),
            ("focus-opinion", 0),
            ("minimal-essay", 0),
            ("lifestyle-emotion", 0),
        ]

    return sorted(scores, key=lambda item: item[1], reverse=True)


def style_theme_policy(style: dict[str, Any]) -> tuple[str, str]:
    raw_theme = str(style.get("theme") or "professional-clean").strip()
    raw_mode = str(style.get("theme_mode") or style.get("theme_strategy") or "").strip().lower()

    if raw_theme.lower() in {"auto", "rotate", "smart", "adaptive"}:
        return "auto", "professional-clean"
    if raw_mode in {"auto", "rotate", "smart", "adaptive"}:
        return "auto", raw_theme or "professional-clean"
    if raw_mode in {"fixed", "lock", "locked"}:
        return "fixed", raw_theme or "professional-clean"
    return "fixed", raw_theme or "professional-clean"


def record_from_paths(article_dir: Path) -> dict[str, Any] | None:
    metadata = load_json(article_dir / "draft-metadata.json")
    plan = load_json(article_dir / "generated" / "layout-plan.json")
    if not metadata and not plan:
        return None

    article_text = ""
    article_path = article_dir / "article.md"
    if article_path.exists():
        try:
            article_text = article_path.read_text(encoding="utf-8")
        except Exception:
            article_text = ""

    title = str(metadata.get("title") or plan.get("title") or article_dir.name)
    pattern = str(
        metadata.get("module_pattern")
        or plan.get("module_pattern")
        or (module_pattern(article_text) if article_text else "")
    )
    return {
        "title": title,
        "path": str(article_dir),
        "source": "output",
        "theme": str(metadata.get("theme") or plan.get("theme") or ""),
        "theme_mode": str(metadata.get("theme_mode") or plan.get("theme_mode") or ""),
        "layout_family": str(metadata.get("layout_family") or plan.get("layout_family") or ""),
        "layout_variant": str(metadata.get("layout_variant") or plan.get("layout_variant") or ""),
        "module_pattern": pattern,
    }


def recent_layout_records(exclude_dir: Path | None = None, limit: int = 12) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    resolved_exclude = exclude_dir.resolve() if exclude_dir else None

    history = load_yaml(SKILL_ROOT / "history.yaml")
    for item in history.get("articles", []) or []:
        if not isinstance(item, dict):
            continue
        record = {
            "title": str(item.get("title") or ""),
            "path": "",
            "source": "history",
            "theme": str(item.get("theme") or ""),
            "theme_mode": str(item.get("theme_mode") or ""),
            "layout_family": str(item.get("layout_family") or ""),
            "layout_variant": str(item.get("layout_variant") or ""),
            "module_pattern": str(item.get("module_pattern") or ""),
        }
        if not any(record.get(key) for key in ("theme", "layout_family", "module_pattern")):
            continue
        key = f"history:{record['title']}:{record['theme']}:{record['layout_family']}"
        if key not in seen:
            seen.add(key)
            records.append(record)

    if OUTPUT_ROOT.exists():
        dirs = [path for path in OUTPUT_ROOT.iterdir() if path.is_dir()]
        dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        for article_dir in dirs:
            if resolved_exclude and article_dir.resolve() == resolved_exclude:
                continue
            if article_dir.name.startswith("_"):
                continue
            if not (article_dir / "article.md").exists():
                continue
            record = record_from_paths(article_dir)
            if not record:
                continue
            key = f"output:{Path(record['path']).resolve()}"
            if key not in seen:
                seen.add(key)
                records.append(record)
            if len(records) >= limit:
                break

    return records[:limit]


def choose_family(title: str, markdown_text: str, recent: list[dict[str, Any]]) -> str:
    ranked = rank_layout_families(title, markdown_text)
    recent_families = [item.get("layout_family") for item in recent[:3] if item.get("layout_family")]
    candidates: list[tuple[str, int]] = []
    for family, score in ranked:
        adjusted = score - recent_families[:2].count(family) * 4 - recent_families[:3].count(family)
        candidates.append((family, adjusted))
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0] if candidates else "professional-info"


def choose_theme(family: str, title: str, recent: list[dict[str, Any]], fallback: str) -> str:
    config = LAYOUT_FAMILIES.get(family, LAYOUT_FAMILIES["professional-info"])
    candidates = list(config["themes"])
    if fallback in candidates:
        candidates.remove(fallback)
        candidates.append(fallback)

    recent_themes = [item.get("theme") for item in recent if item.get("theme")]
    usage = Counter(recent_themes)
    scored: list[tuple[str, int]] = []
    for order, theme in enumerate(rotated(candidates, title)):
        score = 100
        score -= usage[theme] * 4
        score -= recent_themes[:1].count(theme) * 20
        score -= recent_themes[:2].count(theme) * 12
        if theme == fallback:
            score -= 8
        score -= order
        scored.append((theme, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[0][0] if scored else fallback


def choose_suggested_pattern(family: str, title: str, recent: list[dict[str, Any]]) -> str:
    patterns = list(LAYOUT_FAMILIES.get(family, LAYOUT_FAMILIES["professional-info"])["patterns"])
    recent_patterns = [item.get("module_pattern") for item in recent[:4] if item.get("module_pattern")]
    for pattern in rotated(patterns, title):
        if pattern not in recent_patterns:
            return pattern
    return rotated(patterns, title)[0]


def build_layout_plan(
    article_dir: Path,
    article_markdown: str,
    explicit_theme: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    title = extract_title(article_markdown, fallback=str(metadata.get("title") or article_dir.name))
    recent = recent_layout_records(exclude_dir=article_dir)
    style = load_yaml(SKILL_ROOT / "style.yaml")
    mode, fallback_theme = style_theme_policy(style)

    if explicit_theme:
        theme = explicit_theme
        mode = "fixed"
        family = THEME_TO_FAMILY.get(theme) or choose_family(title, article_markdown, recent)
    elif mode == "fixed":
        theme = fallback_theme
        family = THEME_TO_FAMILY.get(theme) or choose_family(title, article_markdown, recent)
    else:
        family = choose_family(title, article_markdown, recent)
        theme = choose_theme(family, title, recent, fallback_theme)

    config = LAYOUT_FAMILIES.get(family, LAYOUT_FAMILIES["professional-info"])
    pattern = module_pattern(article_markdown)
    sequence = extract_module_sequence(article_markdown)
    suggested_pattern = choose_suggested_pattern(family, title, recent)

    return {
        "title": title,
        "theme": theme,
        "theme_mode": mode,
        "layout_family": family,
        "layout_variant": config["variant"],
        "module_pattern": pattern,
        "module_sequence": sequence,
        "suggested_module_pattern": suggested_pattern,
        "recent_compared": [
            {
                "title": item.get("title", ""),
                "theme": item.get("theme", ""),
                "layout_family": item.get("layout_family", ""),
                "module_pattern": item.get("module_pattern", ""),
                "source": item.get("source", ""),
            }
            for item in recent[:5]
        ],
    }


def write_layout_plan(article_dir: Path, plan: dict[str, Any]) -> Path:
    generated_dir = article_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    output_path = generated_dir / "layout-plan.json"
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def evaluate_layout_diversity(
    article_dir: Path,
    metadata: dict[str, Any],
    article_markdown: str,
) -> dict[str, Any]:
    current_theme = str(metadata.get("theme") or "").strip()
    current_mode = str(metadata.get("theme_mode") or "").strip() or "fixed"
    current_family = str(metadata.get("layout_family") or "").strip()
    current_variant = str(metadata.get("layout_variant") or "").strip()
    current_pattern = module_pattern(article_markdown)
    sequence = extract_module_sequence(article_markdown)
    unique_modules = sorted(set(sequence))
    recent = recent_layout_records(exclude_dir=article_dir)
    warnings: list[str] = []

    if not current_theme:
        warnings.append("layout metadata missing: theme")
    if not current_family:
        warnings.append("layout metadata missing: layout_family")
    if not current_variant:
        warnings.append("layout metadata missing: layout_variant")

    structural_modules = [item for item in unique_modules if item != "image"]
    if len(structural_modules) < 2:
        warnings.append("article uses fewer than 2 non-image layout modules")

    if current_mode != "fixed":
        recent_themes = [item.get("theme") for item in recent if item.get("theme")]
        recent_families = [item.get("layout_family") for item in recent if item.get("layout_family")]
        recent_patterns = [item.get("module_pattern") for item in recent if item.get("module_pattern")]

        if len(recent_themes) >= 2 and recent_themes[:2].count(current_theme) == 2:
            warnings.append(f"theme repeats the last 2 comparable articles: {current_theme}")
        if len(recent_families) >= 2 and recent_families[:2].count(current_family) == 2:
            warnings.append(f"layout family repeats the last 2 comparable articles: {current_family}")
        if current_pattern != "plain" and len(recent_patterns) >= 2 and recent_patterns[:2].count(current_pattern) == 2:
            warnings.append(f"module pattern repeats the last 2 comparable articles: {current_pattern}")

    return {
        "status": "warn" if warnings else "pass",
        "warnings": warnings,
        "current": {
            "theme": current_theme,
            "theme_mode": current_mode,
            "layout_family": current_family,
            "layout_variant": current_variant,
            "module_pattern": current_pattern,
            "module_sequence": sequence,
        },
        "recent_compared": recent[:5],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or check WeWrite layout diversity.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Select theme/layout for an article")
    p_plan.add_argument("--article-dir", required=True)
    p_plan.add_argument("--theme", default="")
    p_plan.add_argument("--write", action="store_true")

    p_check = sub.add_parser("check", help="Check layout diversity for an article")
    p_check.add_argument("--article-dir", required=True)

    args = parser.parse_args()
    article_dir = Path(args.article_dir).resolve()
    article_path = article_dir / "article.md"
    metadata_path = article_dir / "draft-metadata.json"
    article_markdown = article_path.read_text(encoding="utf-8") if article_path.exists() else ""
    metadata = load_json(metadata_path)

    if args.command == "plan":
        plan = build_layout_plan(article_dir, article_markdown, explicit_theme=args.theme, metadata=metadata)
        if args.write:
            write_layout_plan(article_dir, plan)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    result = evaluate_layout_diversity(article_dir, metadata, article_markdown)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
