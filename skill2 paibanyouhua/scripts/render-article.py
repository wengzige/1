#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path, PurePosixPath

import yaml
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLKIT_DIR = REPO_ROOT / 'toolkit'
SCRIPTS_DIR = REPO_ROOT / 'scripts'
if str(TOOLKIT_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLKIT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from converter import WeChatConverter, preview_html  # noqa: E402
from humanness_score import score_article  # noqa: E402
from layout_strategy import build_layout_plan, write_layout_plan  # noqa: E402
from theme import load_theme  # noqa: E402


def load_style_theme(default: str = 'professional-clean') -> str:
    style_path = REPO_ROOT / 'style.yaml'
    if not style_path.exists():
        return default
    data = yaml.safe_load(style_path.read_text(encoding='utf-8')) or {}
    return str(data.get('theme') or default)


def load_style_author(default: str = '') -> str:
    style_path = REPO_ROOT / 'style.yaml'
    if not style_path.exists():
        return default
    data = yaml.safe_load(style_path.read_text(encoding='utf-8')) or {}
    return str(data.get('author') or default)


def normalize_image_src(src: str) -> str:
    normalized = src.replace('\\', '/').lstrip('./')
    if normalized.startswith('assets/'):
        return normalized
    pure = PurePosixPath(normalized)
    if len(pure.parts) == 1:
        return f'assets/{pure.name}'
    return normalized


def rewrite_image_sources(html: str, *, use_placeholders: bool) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    for img in soup.find_all('img'):
        src = img.get('src', '').strip()
        if not src or src.startswith(('http://', 'https://')):
            continue
        normalized = normalize_image_src(src)
        img['src'] = f'{{{{IMAGE:{normalized}}}}}' if use_placeholders else normalized
    return str(soup)


def write_utf8(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description='Render article.md into template HTML and preview files.')
    parser.add_argument('--article-dir', required=True)
    parser.add_argument('--theme', default='')
    args = parser.parse_args()

    article_dir = Path(args.article_dir).resolve()
    if not article_dir.exists():
        raise FileNotFoundError(f'article folder not found: {article_dir}')

    article_path = article_dir / 'article.md'
    meta_path = article_dir / 'draft-metadata.json'
    template_path = REPO_ROOT / 'skill2 paibanyouhua' / 'templates' / 'article-body.template.html.template'
    html_output_path = article_dir / 'article-body.template.html'
    preview_output_path = article_dir / 'preview.html'
    generated_dir = article_dir / 'generated'

    if not article_path.exists():
        raise FileNotFoundError(f'article.md not found: {article_path}')
    if not meta_path.exists():
        raise FileNotFoundError(f'draft-metadata.json not found: {meta_path}')
    if not template_path.exists():
        raise FileNotFoundError(f'Template shell not found: {template_path}')

    generated_dir.mkdir(parents=True, exist_ok=True)

    metadata = json.loads(meta_path.read_text(encoding='utf-8'))
    article_markdown = article_path.read_text(encoding='utf-8')
    layout_plan = build_layout_plan(
        article_dir=article_dir,
        article_markdown=article_markdown,
        explicit_theme=args.theme.strip(),
        metadata=metadata,
    )
    theme_name = layout_plan['theme'] or load_style_theme()
    theme = load_theme(theme_name)
    converter = WeChatConverter(theme=theme, layout_variant=layout_plan.get('layout_variant', 'standard'))
    result = converter.convert_file(str(article_path))
    humanness_report_path = generated_dir / 'humanness-report.json'
    layout_plan_path = write_layout_plan(article_dir, layout_plan)

    title = result.title.strip() or str(metadata.get('title') or article_dir.name)
    digest = str(metadata.get('digest') or '').strip() or result.digest
    author = str(metadata.get('author') or '').strip() or load_style_author()
    content_source_url = str(metadata.get('content_source_url') or '')
    cover_image = str(metadata.get('cover_image') or 'assets/cover-wide.jpg')
    need_open_comment = int(metadata.get('need_open_comment', 1))
    only_fans_can_comment = int(metadata.get('only_fans_can_comment', 0))

    publish_body = rewrite_image_sources(result.html, use_placeholders=True)
    preview_body = rewrite_image_sources(result.html, use_placeholders=False)

    shell = template_path.read_text(encoding='utf-8')
    rendered_publish_html = (
        shell.replace('{{TITLE}}', title)
        .replace('{{DIGEST}}', digest)
        .replace('{{CONTENT}}', publish_body)
    )
    rendered_preview_html = (
        shell.replace('{{TITLE}}', title)
        .replace('{{DIGEST}}', digest)
        .replace('{{CONTENT}}', preview_body)
    )

    updated_metadata = dict(metadata)
    updated_metadata.update({
        'title': title,
        'author': author,
        'digest': digest,
        'content_source_url': content_source_url,
        'cover_image': cover_image,
        'need_open_comment': need_open_comment,
        'only_fans_can_comment': only_fans_can_comment,
        'theme': theme_name,
        'theme_mode': layout_plan.get('theme_mode', 'fixed'),
        'layout_family': layout_plan.get('layout_family', ''),
        'layout_variant': layout_plan.get('layout_variant', ''),
        'module_pattern': layout_plan.get('module_pattern', ''),
        'suggested_module_pattern': layout_plan.get('suggested_module_pattern', ''),
    })
    humanness_report = score_article(article_markdown)
    humanness_report['article_path'] = str(article_path)
    humanness_report['report_path'] = str(humanness_report_path)

    write_utf8(meta_path, json.dumps(updated_metadata, ensure_ascii=False, indent=2) + '\n')
    write_utf8(html_output_path, rendered_publish_html)
    write_utf8(preview_output_path, preview_html(rendered_preview_html, theme))
    write_utf8(humanness_report_path, json.dumps(humanness_report, ensure_ascii=False, indent=2) + '\n')

    print(json.dumps({
        'article_dir': str(article_dir),
        'title': title,
        'digest': digest,
        'theme': theme_name,
        'layout_family': layout_plan.get('layout_family', ''),
        'module_pattern': layout_plan.get('module_pattern', ''),
        'layout_plan': str(layout_plan_path),
        'html_template': str(html_output_path),
        'preview_html': str(preview_output_path),
        'humanness_report': str(humanness_report_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
