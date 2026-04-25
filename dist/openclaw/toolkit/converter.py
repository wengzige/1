"""
Markdown to WeChat-compatible HTML converter.

Forked from wechat_article_skills/scripts/markdown_to_html.py,
adapted for YAML-driven themes and agent integration.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import markdown
from bs4 import BeautifulSoup
from bs4.element import Comment

from theme import Theme, load_theme, get_inline_css_rules


@dataclass
class ConvertResult:
    """Result of a Markdown → WeChat HTML conversion."""

    html: str  # WeChat-compatible inline-style HTML (body content only)
    title: str  # Extracted H1 title
    digest: str  # Auto-generated summary (first 120 chars)
    images: list[str] = field(default_factory=list)  # Image references found


class WeChatConverter:
    """Convert Markdown to WeChat-compatible inline-style HTML."""

    def __init__(
        self,
        theme: Optional[Theme] = None,
        theme_name: str = "professional-clean",
        layout_variant: str = "standard",
    ):
        if theme is not None:
            self._theme = theme
        else:
            self._theme = load_theme(theme_name)
        self._layout_variant = layout_variant or "standard"
        self._css_rules = get_inline_css_rules(self._theme)

    def convert(self, markdown_text: str) -> ConvertResult:
        """
        Convert Markdown text to WeChat-compatible HTML.

        Returns ConvertResult with:
          - html: inline-style HTML (body content only, no <html>/<head> wrapper)
          - title: extracted H1 title (or empty string)
          - digest: first 120 characters of plain text
          - images: list of image src references
        """
        markdown_text = self._strip_front_matter(markdown_text)
        title = self._extract_title(markdown_text)
        markdown_text = self._strip_h1(markdown_text)

        # Pre-process container blocks (:::dialogue, :::timeline, etc.)
        markdown_text = self._preprocess_containers(markdown_text)

        # CJK fix: auto-space between CJK and Latin characters
        markdown_text = self._fix_cjk_spacing(markdown_text)

        # Parse Markdown → HTML
        html = self._markdown_to_html(markdown_text)

        # Strip HTML comments so editor notes never leak into previews/drafts.
        html = self._strip_html_comments(html)

        # Enhance code blocks (add data-lang attribute)
        html = self._enhance_code_blocks(html)

        # Process images (ensure responsive styling)
        html, images = self._process_images(html)

        # CJK fix: move punctuation outside bold tags
        html = self._fix_cjk_bold_punctuation(html)

        # CJK fix: convert ul/ol to section-based lists (WeChat renders native lists unreliably)
        html = self._convert_lists_to_sections(html)

        # Convert external links to footnotes (WeChat blocks external links)
        html = self._convert_links_to_footnotes(html)

        # Apply inline CSS from theme
        html = self._apply_inline_styles(html)

        # Apply WeChat compatibility fixes
        html = self._apply_wechat_fixes(html)

        # Inject dark mode attributes
        html = self._inject_darkmode(html)

        # Generate digest from plain text
        digest = self._generate_digest(html)

        return ConvertResult(html=html, title=title, digest=digest, images=images)

    def convert_file(self, input_path: str) -> ConvertResult:
        """Convert a Markdown file."""
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        text = path.read_text(encoding="utf-8")
        return self.convert(text)

    # -- internal methods --

    def _extract_title(self, text: str) -> str:
        """Extract the first H1 title from Markdown text."""
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                return stripped[2:].strip()
        return ""

    def _strip_front_matter(self, text: str) -> str:
        """Remove YAML front matter from the beginning of a Markdown file."""
        normalized = text.replace("\r\n", "\n")
        if not normalized.startswith("---\n"):
            return text

        end = normalized.find("\n---\n", 4)
        if end == -1:
            return text

        stripped = normalized[end + len("\n---\n") :]
        if text.startswith("---\r\n"):
            return stripped.replace("\n", "\r\n")
        return stripped

    def _strip_h1(self, text: str) -> str:
        """Remove H1 lines — WeChat has a separate title field."""
        lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                continue
            lines.append(line)
        return "\n".join(lines)

    def _markdown_to_html(self, text: str) -> str:
        """Parse Markdown to HTML using python-markdown with extensions."""
        extensions = [
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
            "markdown.extensions.codehilite",
        ]
        extension_configs = {
            "codehilite": {
                "linenums": False,
                "guess_lang": True,
                "noclasses": True,  # Inline syntax highlight styles
            }
        }
        md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
        return md.convert(text)

    def _enhance_code_blocks(self, html: str) -> str:
        """Add data-lang attribute to <pre> elements for language labeling."""
        soup = BeautifulSoup(html, "html.parser")
        for pre in soup.find_all("pre"):
            code = pre.find("code")
            if code:
                for cls in code.get("class", []):
                    if cls.startswith("language-"):
                        pre["data-lang"] = cls.replace("language-", "")
                        break
        return str(soup)

    def _strip_html_comments(self, html: str) -> str:
        """Remove HTML comments so internal notes do not appear in output."""
        soup = BeautifulSoup(html, "html.parser")
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        return str(soup)

    def _process_images(self, html: str) -> tuple[str, list[str]]:
        """Extract image references and ensure responsive styling."""
        soup = BeautifulSoup(html, "html.parser")
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                images.append(src)
            # Ensure responsive image styles
            existing = img.get("style", "")
            if "max-width" not in existing:
                additions = "max-width: 100%; height: auto; display: block; margin: 24px auto"
                img["style"] = f"{existing}; {additions}" if existing else additions
        return str(soup), images

    def _apply_inline_styles(self, html: str) -> str:
        """Apply theme CSS rules as inline styles on matching elements."""
        soup = BeautifulSoup(html, "html.parser")

        for selector, styles in self._css_rules.items():
            # Skip body — we don't wrap in body tag
            if selector.strip() == "body":
                continue

            try:
                elements = soup.select(selector)
            except Exception:
                continue

            for elem in elements:
                existing = elem.get("style", "")
                style_dict = {}

                # Parse existing inline styles
                if existing:
                    for item in existing.split(";"):
                        if ":" in item:
                            key, val = item.split(":", 1)
                            style_dict[key.strip()] = val.strip()

                # Add theme styles (existing styles take precedence)
                for prop, val in styles.items():
                    if prop not in style_dict:
                        style_dict[prop] = val

                elem["style"] = "; ".join(f"{k}: {v}" for k, v in style_dict.items())

        return str(soup)

    def _apply_wechat_fixes(self, html: str) -> str:
        """
        Apply WeChat-specific compatibility fixes:
        1. Force explicit color on every <p> tag
        2. Ensure code blocks preserve whitespace
        """
        soup = BeautifulSoup(html, "html.parser")
        text_color = self._theme.colors.get("text", "#333333")

        # Fix 1: Ensure all <p> tags have explicit color
        for p in soup.find_all("p"):
            style = p.get("style", "")
            if "color" not in style:
                p["style"] = f"{style}; color: {text_color}" if style else f"color: {text_color}"

        # Fix 2: Ensure <pre> has whitespace preservation
        for pre in soup.find_all("pre"):
            style = pre.get("style", "")
            if "white-space" not in style:
                pre["style"] = f"{style}; white-space: pre-wrap; word-wrap: break-word" if style else "white-space: pre-wrap; word-wrap: break-word"

        return str(soup)

    # -- CJK compatibility fixes --

    def _fix_cjk_spacing(self, text: str) -> str:
        """Auto-insert thin space between CJK and Latin/digit characters.

        WeChat renders CJK-Latin without spacing, making mixed text hard to read.
        This inserts a thin space (U+200A) at CJK↔Latin boundaries.
        Runs on raw Markdown before parsing, skipping code blocks and links.
        """
        # CJK unicode ranges
        cjk = r'[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef]'
        latin = r'[A-Za-z0-9]'

        lines = text.split('\n')
        result = []
        in_code_block = False

        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                result.append(line)
                continue
            if in_code_block:
                result.append(line)
                continue

            # CJK followed by Latin
            line = re.sub(f'({cjk})({latin})', r'\1 \2', line)
            # Latin followed by CJK
            line = re.sub(f'({latin})({cjk})', r'\1 \2', line)
            result.append(line)

        return '\n'.join(result)

    def _fix_cjk_bold_punctuation(self, html: str) -> str:
        """Move Chinese punctuation outside bold/strong tags.

        WeChat renders bold CJK punctuation with ugly spacing.
        Move trailing punctuation (，。！？；：、) outside </strong>.
        """
        # Match: <strong>内容+中文标点</strong> → <strong>内容</strong>标点
        pattern = r'(<strong>)(.*?)([，。！？；：、]+)(</strong>)'
        return re.sub(pattern, r'\1\2\4\3', html)

    def _convert_lists_to_sections(self, html: str) -> str:
        """Convert <ul>/<ol> to styled <section> elements.

        WeChat's native list rendering is unreliable (inconsistent bullet
        style, broken indentation on some devices). Using section+span
        for bullets/numbers gives full control over appearance.
        """
        soup = BeautifulSoup(html, "html.parser")
        text_color = self._theme.colors.get("text", "#333333")
        primary = self._theme.colors.get("primary", "#2563eb")

        for ul in soup.find_all("ul"):
            section = soup.new_tag("section")
            for li in ul.find_all("li", recursive=False):
                item = soup.new_tag("section", style=f"display: flex; align-items: flex-start; margin-bottom: 8px; color: {text_color}")
                bullet = soup.new_tag("span", style=f"color: {primary}; margin-right: 8px; flex-shrink: 0; font-size: 18px; line-height: 1.6")
                bullet.string = "•"
                content = soup.new_tag("span", style="flex: 1")
                for child in list(li.children):
                    content.append(child.extract() if hasattr(child, 'extract') else child)
                item.append(bullet)
                item.append(content)
                section.append(item)
            ul.replace_with(section)

        for idx, ol in enumerate(soup.find_all("ol")):
            section = soup.new_tag("section")
            for num, li in enumerate(ol.find_all("li", recursive=False), 1):
                item = soup.new_tag("section", style=f"display: flex; align-items: flex-start; margin-bottom: 8px; color: {text_color}")
                number = soup.new_tag("span", style=f"color: {primary}; margin-right: 8px; flex-shrink: 0; font-weight: 700; line-height: 1.8")
                number.string = f"{num}."
                content = soup.new_tag("span", style="flex: 1")
                for child in list(li.children):
                    content.append(child.extract() if hasattr(child, 'extract') else child)
                item.append(number)
                item.append(content)
                section.append(item)
            ol.replace_with(section)

        return str(soup)

    # -- External link → footnote conversion --

    def _convert_links_to_footnotes(self, html: str) -> str:
        """Convert external <a> links to superscript footnote numbers.

        WeChat blocks external links — readers see dead text. This converts
        each external link to a superscript number with the URL collected
        into a reference list appended at the end.
        """
        soup = BeautifulSoup(html, "html.parser")
        footnotes = []
        counter = 0
        primary = self._theme.colors.get("primary", "#2563eb")

        for a in soup.find_all("a"):
            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue  # skip anchors

            counter += 1
            text = a.get_text()
            footnotes.append((counter, text, href))

            # Replace <a> with text + superscript number
            sup = soup.new_tag("sup")
            sup_link = soup.new_tag("span", style=f"color: {primary}; font-size: 12px")
            sup_link.string = f"[{counter}]"
            sup.append(sup_link)
            a.replace_with(text, sup)

        if footnotes:
            # Append reference section
            hr = soup.new_tag("hr", style="border: none; border-top: 1px solid #e5e5e5; margin: 32px 0 16px")
            soup.append(hr)
            ref_title = soup.new_tag("p", style="font-size: 13px; color: #999999; margin-bottom: 8px; font-weight: 700")
            ref_title.string = "参考链接"
            soup.append(ref_title)
            for num, text, href in footnotes:
                ref = soup.new_tag("p", style="font-size: 12px; color: #999999; margin: 2px 0; word-break: break-all")
                ref.string = f"[{num}] {text}: {href}"
                soup.append(ref)

        return str(soup)

    # -- Dark mode --

    def _inject_darkmode(self, html: str) -> str:
        """Inject data-darkmode-* attributes for WeChat dark mode.

        WeChat auto-inverts colors in dark mode, which often breaks
        designed color schemes. Explicit darkmode attributes tell WeChat
        exactly what colors to use instead of guessing.
        """
        darkmode = self._theme.colors.get("darkmode", {})
        if not darkmode:
            return html

        soup = BeautifulSoup(html, "html.parser")
        dm_text = darkmode.get("text", "#c8c8c8")
        dm_bg = darkmode.get("background", "#1e1e1e")
        dm_primary = darkmode.get("primary", "#6aadff")

        # Body-level elements (p, li, section, span)
        for tag_name in ("p", "span", "section"):
            for elem in soup.find_all(tag_name):
                style = elem.get("style", "")
                # Only set if element has a color
                if "color" in style:
                    elem["data-darkmode-color"] = dm_text
                    elem["data-darkmode-bgcolor"] = "transparent"

        # Headings
        dm_heading = darkmode.get("text", "#e0e0e0")
        for tag_name in ("h1", "h2", "h3", "h4"):
            for elem in soup.find_all(tag_name):
                elem["data-darkmode-color"] = dm_heading
                elem["data-darkmode-bgcolor"] = "transparent"

        # Code blocks
        dm_code_bg = darkmode.get("code_bg", "#2d2d2d")
        dm_code_color = darkmode.get("code_color", "#d4d4d4")
        for pre in soup.find_all("pre"):
            pre["data-darkmode-bgcolor"] = dm_code_bg
            pre["data-darkmode-color"] = dm_code_color
        for code in soup.find_all("code"):
            code["data-darkmode-color"] = dm_code_color

        # Blockquotes
        dm_quote_bg = darkmode.get("quote_bg", "#2a2a2a")
        for bq in soup.find_all("blockquote"):
            bq["data-darkmode-bgcolor"] = dm_quote_bg
            bq["data-darkmode-color"] = dm_text

        # Strong/em with primary color
        for strong in soup.find_all("strong"):
            strong["data-darkmode-color"] = dm_primary

        return str(soup)

    # -- Container block syntax --

    def _preprocess_containers(self, text: str) -> str:
        """Pre-process :::container blocks into styled HTML before Markdown parsing.

        Supports:
          :::dialogue   — chat bubble layout
          :::timeline   — vertical timeline with dots
          :::callout    — Obsidian-style callout (tip/warning/info/danger)
          :::quote      — styled pull quote
        """
        text = self._process_dialogue(text)
        text = self._process_timeline(text)
        text = self._process_callout(text)
        text = self._process_quote_block(text)
        return text

    def _layout_profile(self) -> dict[str, str]:
        """Return small style switches for generated container blocks."""
        primary = self._theme.colors.get("primary", "#2563eb")
        text = self._theme.colors.get("text", "#333333")
        profiles = {
            "info-flow": {
                "primary": primary,
                "text": text,
                "soft_bg": "#f8fafc",
                "muted_bg": "#f1f5f9",
                "shape": "10px",
                "accent": "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)",
            },
            "tech-magazine": {
                "primary": primary,
                "text": text,
                "soft_bg": "#f8f5ff",
                "muted_bg": "#f3f4f6",
                "shape": "14px",
                "accent": "linear-gradient(135deg, #eff6ff 0%, #f5f3ff 100%)",
            },
            "editorial": {
                "primary": primary,
                "text": text,
                "soft_bg": "#fff7ed",
                "muted_bg": "#f8f5f0",
                "shape": "2px",
                "accent": "linear-gradient(180deg, #fffaf4 0%, #ffffff 100%)",
            },
            "focus": {
                "primary": primary,
                "text": text,
                "soft_bg": "#fff1f2",
                "muted_bg": "#f8fafc",
                "shape": "0",
                "accent": "#fff7f7",
            },
            "minimal": {
                "primary": primary,
                "text": text,
                "soft_bg": "#ffffff",
                "muted_bg": "#fafafa",
                "shape": "0",
                "accent": "#ffffff",
            },
            "warm": {
                "primary": primary,
                "text": text,
                "soft_bg": "#fff1f2",
                "muted_bg": "#fff7ed",
                "shape": "18px",
                "accent": "linear-gradient(135deg, #fff1f2 0%, #fff7ed 100%)",
            },
        }
        return profiles.get(
            self._layout_variant,
            {
                "primary": primary,
                "text": text,
                "soft_bg": "#eff6ff",
                "muted_bg": "#f3f4f6",
                "shape": "8px",
                "accent": "linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)",
            },
        )

    def _process_dialogue(self, text: str) -> str:
        """Convert :::dialogue blocks to chat bubble HTML."""
        profile = self._layout_profile()
        primary = profile["primary"]
        muted_bg = profile["muted_bg"]
        radius = profile["shape"]
        variant = self._layout_variant

        def replace_dialogue(match):
            content = match.group(1).strip()
            bubbles = []
            for idx, line in enumerate(content.split('\n')):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('> '):
                    # Right-aligned (reply) bubble
                    msg = line[2:].strip()
                    if variant == "minimal":
                        bubbles.append(
                            f'<section style="text-align: right; margin: 14px 0; font-size: 15px; line-height: 1.8; color: {primary}; border-right: 2px solid {primary}; padding-right: 12px">{msg}</section>'
                        )
                    elif variant == "focus":
                        bubbles.append(
                            f'<section style="display: flex; justify-content: flex-end; margin-bottom: 10px">'
                            f'<section style="background: {primary}; color: white; padding: 10px 14px; border-radius: 2px; max-width: 82%; font-size: 15px; line-height: 1.65; font-weight: 600">{msg}</section></section>'
                        )
                    else:
                        bubbles.append(f'<section style="display: flex; justify-content: flex-end; margin-bottom: 12px">'
                                       f'<section style="background: {primary}; color: white; padding: 10px 14px; border-radius: {radius} {radius} 2px {radius}; max-width: 80%; font-size: 15px; line-height: 1.6">{msg}</section></section>')
                else:
                    # Left-aligned bubble
                    if variant == "editorial":
                        label = "问" if idx == 0 else "答"
                        bubbles.append(
                            f'<section style="margin: 12px 0; padding: 12px 14px; background: {muted_bg}; border-left: 3px solid {primary}; font-size: 15px; line-height: 1.75; color: #333"><strong>{label}：</strong>{line}</section>'
                        )
                    elif variant == "minimal":
                        bubbles.append(
                            f'<section style="margin: 14px 0; font-size: 15px; line-height: 1.8; color: #333; border-left: 2px solid #d4d4d4; padding-left: 12px">{line}</section>'
                        )
                    else:
                        bubbles.append(f'<section style="display: flex; justify-content: flex-start; margin-bottom: 12px">'
                                       f'<section style="background: {muted_bg}; color: #333; padding: 10px 14px; border-radius: {radius} {radius} {radius} 2px; max-width: 80%; font-size: 15px; line-height: 1.6">{line}</section></section>')
            return '\n'.join(bubbles)

        return re.sub(r':::dialogue\n(.*?)\n:::', replace_dialogue, text, flags=re.DOTALL)

    def _process_timeline(self, text: str) -> str:
        """Convert :::timeline blocks to vertical timeline HTML."""
        profile = self._layout_profile()
        primary = profile["primary"]
        soft_bg = profile["soft_bg"]
        variant = self._layout_variant

        def replace_timeline(match):
            content = match.group(1).strip()
            items = []
            for index, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line:
                    continue
                # Format: "**title** description" or just "description"
                if variant == "tech-magazine":
                    items.append(
                        f'<section style="display: flex; margin: 12px 0; background: {soft_bg}; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px">'
                        f'<section style="flex-shrink: 0; width: 34px; height: 34px; border-radius: 8px; background: {primary}; color: #fff; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; margin-right: 12px">{index:02d}</section>'
                        f'<section style="flex: 1; font-size: 15px; line-height: 1.7">{line}</section>'
                        f'</section>'
                    )
                elif variant == "focus":
                    items.append(
                        f'<section style="display: flex; margin: 14px 0; border-bottom: 1px solid #e5e7eb; padding-bottom: 12px">'
                        f'<section style="flex-shrink: 0; color: {primary}; font-size: 24px; font-weight: 800; line-height: 1; margin-right: 12px">{index}</section>'
                        f'<section style="flex: 1; font-size: 15px; line-height: 1.75; font-weight: 500">{line}</section>'
                        f'</section>'
                    )
                elif variant == "minimal":
                    items.append(
                        f'<section style="margin: 14px 0; padding-left: 16px; border-left: 1px solid #d4d4d4; font-size: 15px; line-height: 1.8">{line}</section>'
                    )
                else:
                    items.append(
                        f'<section style="display: flex; margin-bottom: 16px">'
                        f'<section style="flex-shrink: 0; width: 12px; display: flex; flex-direction: column; align-items: center">'
                        f'<section style="width: 10px; height: 10px; border-radius: 50%; background: {primary}; margin-top: 6px"></section>'
                        f'<section style="width: 2px; flex: 1; background: #e5e7eb; margin-top: 4px"></section>'
                        f'</section>'
                        f'<section style="flex: 1; padding-left: 12px; padding-bottom: 8px; font-size: 15px; line-height: 1.7">{line}</section>'
                        f'</section>'
                    )
            return '\n'.join(items)

        return re.sub(r':::timeline\n(.*?)\n:::', replace_timeline, text, flags=re.DOTALL)

    def _process_callout(self, text: str) -> str:
        """Convert :::callout blocks to styled callout boxes.

        Syntax: :::callout tip/warning/info/danger
        """
        profile = self._layout_profile()
        primary = profile["primary"]
        variant = self._layout_variant
        colors_map = {
            "tip": ("#059669", "#ecfdf5", "💡"),
            "warning": ("#d97706", "#fffbeb", "⚠️"),
            "info": (primary, profile["soft_bg"], "ℹ️"),
            "danger": ("#dc2626", "#fef2f2", "🚨"),
        }

        def replace_callout(match):
            ctype = match.group(1).strip().lower()
            content = match.group(2).strip()
            color, bg, icon = colors_map.get(ctype, colors_map["info"])
            if variant == "focus":
                return (
                    f'<section style="background: {bg}; border-top: 4px solid {color}; border-bottom: 1px solid {color}; '
                    f'padding: 14px 16px; margin: 18px 0; font-size: 15px; line-height: 1.75">'
                    f'<section style="font-weight: 800; color: {color}; margin-bottom: 6px; letter-spacing: 0.08em">{ctype.upper()}</section>'
                    f'{content}</section>'
                )
            if variant == "minimal":
                return (
                    f'<section style="background: #ffffff; border-left: 1px solid {color}; '
                    f'padding: 8px 0 8px 14px; margin: 20px 0; font-size: 15px; line-height: 1.85">'
                    f'<section style="font-weight: 700; color: {color}; margin-bottom: 4px">{ctype.upper()}</section>'
                    f'{content}</section>'
                )
            if variant == "tech-magazine":
                return (
                    f'<section style="background: {profile["accent"]}; border: 1px solid {color}; '
                    f'padding: 16px 16px; border-radius: 14px; margin: 18px 0; font-size: 15px; line-height: 1.75; box-shadow: 0 6px 18px rgba(37, 99, 235, 0.08)">'
                    f'<section style="font-weight: 800; color: {color}; margin-bottom: 8px">{icon} {ctype.upper()}</section>'
                    f'{content}</section>'
                )
            if variant == "info-flow":
                return (
                    f'<section style="background: {profile["accent"]}; border: 1px solid #e5e7eb; border-left: 6px solid {color}; '
                    f'padding: 14px 16px; border-radius: 10px; margin: 18px 0; font-size: 15px; line-height: 1.75">'
                    f'<section style="font-weight: 800; color: {color}; margin-bottom: 6px">{ctype.upper()}</section>'
                    f'{content}</section>'
                )
            return (f'<section style="background: {bg}; border-left: 4px solid {color}; '
                    f'padding: 14px 16px; border-radius: 4px; margin: 16px 0; font-size: 15px; line-height: 1.7">'
                    f'<section style="font-weight: 700; color: {color}; margin-bottom: 6px">{icon} {ctype.upper()}</section>'
                    f'{content}</section>')

        return re.sub(r':::callout\s+(\w+)\n(.*?)\n:::', replace_callout, text, flags=re.DOTALL)

    def _process_quote_block(self, text: str) -> str:
        """Convert :::quote blocks to styled pull quotes."""
        profile = self._layout_profile()
        primary = profile["primary"]
        variant = self._layout_variant

        def replace_quote(match):
            content = match.group(1).strip()
            if variant == "focus":
                return (
                    f'<section style="margin: 26px 0; padding: 18px 0; border-top: 3px solid {primary}; border-bottom: 1px solid {primary}">'
                    f'<section style="font-size: 20px; line-height: 1.75; color: #111; font-weight: 800">'
                    f'{content}</section></section>'
                )
            if variant == "minimal":
                return (
                    f'<section style="margin: 28px 0; padding: 4px 0 4px 18px; border-left: 1px solid {primary}">'
                    f'<section style="font-size: 18px; line-height: 1.9; color: #222; font-style: italic">'
                    f'{content}</section></section>'
                )
            if variant == "editorial":
                return (
                    f'<section style="margin: 26px 0; padding: 20px 22px; background: {profile["accent"]}; border-radius: 2px">'
                    f'<section style="font-size: 20px; line-height: 1.85; color: #2b2118; font-family: Georgia, \"Times New Roman\", \"Noto Serif CJK SC\", serif">'
                    f'“{content}”</section></section>'
                )
            if variant == "tech-magazine":
                return (
                    f'<section style="margin: 24px 0; padding: 18px 20px; border: 1px solid {primary}; border-radius: 14px; background: {profile["accent"]}">'
                    f'<section style="font-size: 18px; line-height: 1.8; color: #111827; font-weight: 700">'
                    f'{content}</section></section>'
                )
            return (f'<section style="margin: 24px 0; padding: 20px 24px; border-left: 4px solid {primary}; '
                    f'background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); border-radius: 0 8px 8px 0">'
                    f'<section style="font-size: 18px; line-height: 1.8; color: #333; font-style: italic">'
                    f'"{content}"</section></section>')

        return re.sub(r':::quote\n(.*?)\n:::', replace_quote, text, flags=re.DOTALL)

    # -- Digest generation --

    def _generate_digest(self, html: str, max_bytes: int = 120) -> str:
        """Generate a digest that fits within WeChat's byte limit (120 bytes UTF-8)."""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()

        # Truncate to fit within max_bytes (UTF-8)
        ellipsis = "..."
        ellipsis_bytes = len(ellipsis.encode("utf-8"))
        target_bytes = max_bytes - ellipsis_bytes

        encoded = text.encode("utf-8")
        if len(encoded) <= max_bytes:
            return text

        # Truncate at valid UTF-8 boundary
        truncated = encoded[:target_bytes].decode("utf-8", errors="ignore").rstrip()
        return truncated + ellipsis


def preview_html(body_html: str, theme: Theme) -> str:
    """
    Wrap body content in a full HTML document for browser preview.
    This is only for local preview — NOT for WeChat publishing.
    """
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview</title>
    <style>
{theme.base_css}
    </style>
</head>
<body>
    {body_html}
</body>
</html>"""
