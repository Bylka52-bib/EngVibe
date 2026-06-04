import re

import bleach
from django.utils.html import escape

try:
    from bleach.css_sanitizer import CSSSanitizer

    CSS_SANITIZER = CSSSanitizer(
        allowed_css_properties=[
            'background',
            'background-color',
            'border-color',
            'color',
            'text-align',
            'vertical-align',
            'width',
            'max-width',
            'float',
            'margin',
            'margin-left',
            'margin-right',
            'margin-bottom',
        ],
    )
except ImportError:
    CSS_SANITIZER = None

YOUTUBE_EMBED_RE = re.compile(
    r'^https://(www\.)?youtube\.com/embed/[A-Za-z0-9_-]+(\?.*)?$'
)
YOUTUBE_WATCH_RE = re.compile(
    r'(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]+)'
)

ALLOWED_CLASSES = frozenset({
    'lesson-align-left',
    'lesson-align-right',
    'lesson-align-center',
    'lesson-media-row',
    'lesson-media-row--img-right',
    'lesson-media-row--img-left',
    'lesson-media-row__body',
    'lesson-media-row__media',
    'lesson-callout',
    'lesson-btn-wrap',
    'lesson-btn',
    'lesson-video-wrap',
    'lesson-table-scroll',
    'lesson-table-float-right',
    'lesson-table-float-left',
})

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'del',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'a', 'img',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
    'blockquote', 'pre', 'code', 'span', 'div',
    'iframe', 'hr', 'sub', 'sup', 'figure', 'figcaption',
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'style'],
    'a': ['href', 'title', 'target', 'rel', 'class', 'style'],
    'img': ['src', 'alt', 'title', 'width', 'height', 'loading', 'class', 'style'],
    'iframe': ['src', 'title', 'allow', 'allowfullscreen', 'referrerpolicy', 'loading', 'class'],
    'td': ['colspan', 'rowspan', 'class', 'style', 'bgcolor'],
    'th': ['colspan', 'rowspan', 'class', 'style', 'bgcolor'],
    'tr': ['class', 'style'],
    'table': ['class', 'style', 'border', 'cellpadding', 'cellspacing'],
    'div': ['class', 'style'],
    'span': ['class', 'style'],
    'p': ['class', 'style'],
}

HEX_COLOR_RE = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')


def youtube_watch_to_embed(url):
    match = YOUTUBE_WATCH_RE.search(url or '')
    if not match:
        return None
    return f'https://www.youtube.com/embed/{match.group(1)}'


def _filter_iframes(html):
    parts = re.split(r'(<iframe[^>]*>.*?</iframe>)', html, flags=re.IGNORECASE | re.DOTALL)
    out = []
    for part in parts:
        if part.lower().startswith('<iframe'):
            src_match = re.search(r'src=["\']([^"\']+)["\']', part, re.IGNORECASE)
            src = src_match.group(1) if src_match else ''
            embed = youtube_watch_to_embed(src) or src
            if embed and YOUTUBE_EMBED_RE.match(embed):
                safe_src = escape(embed, quote=True)
                out.append(
                    f'<div class="lesson-video-wrap">'
                    f'<iframe src="{safe_src}" title="YouTube video" '
                    f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                    f'allowfullscreen loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe>'
                    f'</div>'
                )
            continue
        out.append(part)
    return ''.join(out)


def _plain_text_to_html(text):
    blocks = [b.strip() for b in str(text).split('\n\n') if b.strip()]
    if not blocks:
        return ''
    parts = []
    for block in blocks:
        safe = escape(block).replace('\n', '<br>')
        parts.append(f'<p>{safe}</p>')
    return ''.join(parts)


_STYLE_ATTR_RE = re.compile(r'\sstyle="([^"]*)"', re.IGNORECASE)
_MCE_STYLE_ATTR_RE = re.compile(r'\sdata-mce-style="([^"]*)"', re.IGNORECASE)


def _normalize_style_value(style_val):
    if not style_val:
        return ''
    parts = []
    for chunk in style_val.split(';'):
        if ':' not in chunk:
            continue
        prop, _, val = chunk.partition(':')
        prop = prop.strip().lower()
        val = val.strip()
        if not val:
            continue
        if prop == 'background':
            prop = 'background-color'
        parts.append(f'{prop}: {val}')
    return '; '.join(parts)


def _prepare_tinymce_html(html):
    """Переносит data-mce-style в style и нормализует background → background-color."""
    tags_with_style = (
        'td', 'th', 'tr', 'table', 'span', 'p', 'div', 'img', 'a',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    )
    tag_pattern = r'<(' + '|'.join(tags_with_style) + r')\b[^>]*>'

    def merge_tag(match):
        tag = match.group(0)
        mce_match = _MCE_STYLE_ATTR_RE.search(tag)
        style_match = _STYLE_ATTR_RE.search(tag)
        mce_val = _normalize_style_value(mce_match.group(1)) if mce_match else ''
        style_val = _normalize_style_value(style_match.group(1)) if style_match else ''
        combined = '; '.join(p for p in (style_val, mce_val) if p)
        tag = _MCE_STYLE_ATTR_RE.sub('', tag)
        tag = _STYLE_ATTR_RE.sub('', tag)
        if combined:
            tag = tag[:-1] + f' style="{combined}">'
        return tag

    html = re.sub(tag_pattern, merge_tag, html, flags=re.IGNORECASE)
    return html


def _filter_classes(html):
    def repl(match):
        classes = match.group(1).split()
        kept = [c for c in classes if c in ALLOWED_CLASSES]
        if not kept:
            return ''
        return f' class="{" ".join(kept)}"'

    return re.sub(r'\sclass="([^"]*)"', repl, html)


def _sanitize_bgcolor(html):
    def repl(match):
        val = match.group(1).strip()
        if HEX_COLOR_RE.match(val):
            return f' bgcolor="{val}"'
        return ''

    return re.sub(r'\sbgcolor="([^"]*)"', repl, html, flags=re.IGNORECASE)


def _sanitize_inline_styles_fallback(html):
    """Резервная очистка style=, если нет tinycss2/CSSSanitizer."""
    allowed_props = {
        'background': re.compile(
            r'^(#[0-9a-fA-F]{3,8}|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(\s*,\s*[\d.]+)?\s*\))$',
            re.I,
        ),
        'background-color': re.compile(
            r'^(#[0-9a-fA-F]{3,8}|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(\s*,\s*[\d.]+)?\s*\))$',
            re.I,
        ),
        'border-color': re.compile(
            r'^(#[0-9a-fA-F]{3,8}|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(\s*,\s*[\d.]+)?\s*\))$',
            re.I,
        ),
        'color': re.compile(
            r'^(#[0-9a-fA-F]{3,8}|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(\s*,\s*[\d.]+)?\s*\))$',
            re.I,
        ),
        'text-align': re.compile(r'^(left|right|center|justify)$', re.I),
        'vertical-align': re.compile(r'^(top|middle|bottom|baseline)$', re.I),
        'float': re.compile(r'^(left|right|none)$', re.I),
        'width': re.compile(r'^(\d+(\.\d+)?(px|%|em)|auto)$', re.I),
        'max-width': re.compile(r'^(\d+(\.\d+)?(px|%|em))$', re.I),
        'margin': re.compile(r'^[\d.\s]+(px|em|%)(\s+[\d.\s]+(px|em|%)){0,3}$', re.I),
        'margin-left': re.compile(r'^(\d+(\.\d+)?(px|em|%)|auto)$', re.I),
        'margin-right': re.compile(r'^(\d+(\.\d+)?(px|em|%)|auto)$', re.I),
        'margin-bottom': re.compile(r'^(\d+(\.\d+)?(px|em|%))$', re.I),
    }

    def clean_style(style_val):
        safe_parts = []
        for chunk in style_val.split(';'):
            if ':' not in chunk:
                continue
            prop, _, val = chunk.partition(':')
            prop = prop.strip().lower()
            val = val.strip()
            pattern = allowed_props.get(prop)
            if pattern and pattern.match(val):
                safe_parts.append(f'{prop}: {val}')
        return '; '.join(safe_parts)

    def tag_repl(match):
        tag = match.group(0)
        style_match = re.search(r'\sstyle="([^"]*)"', tag, re.IGNORECASE)
        if not style_match:
            return tag
        safe = clean_style(style_match.group(1))
        tag = re.sub(r'\sstyle="[^"]*"', '', tag, flags=re.IGNORECASE)
        if safe:
            tag = tag[:-1] + f' style="{safe}">'
        return tag

    return re.sub(
        r'<(td|th|tr|table|img|div|p|span|a|h[1-6])\b[^>]*>',
        tag_repl,
        html,
        flags=re.IGNORECASE,
    )


def _add_lazy_loading_to_images(html):
    def repl(match):
        tag = match.group(0)
        if re.search(r'\bloading\s*=', tag, re.IGNORECASE):
            return tag
        if tag.rstrip().endswith('/>'):
            return tag.rstrip()[:-2] + ' loading="lazy" />'
        if tag.endswith('>'):
            return tag[:-1] + ' loading="lazy">'
        return tag

    return re.sub(r'<img\b[^>]*\/?>', repl, html, flags=re.IGNORECASE)


def _wrap_tables(html):
    def wrap_bare_tables(chunk):
        return re.sub(
            r'(<table[^>]*>.*?</table>)',
            r'<div class="lesson-table-scroll">\1</div>',
            chunk,
            flags=re.DOTALL | re.IGNORECASE,
        )

    if 'lesson-table-scroll' not in html:
        return wrap_bare_tables(html)

    parts = re.split(
        r'(<div class="lesson-table-scroll">.*?</div>)',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return ''.join(
        part if part.lower().startswith('<div class="lesson-table-scroll"') else wrap_bare_tables(part)
        for part in parts
    )


def sanitize_lesson_html(html):
    if not html or not str(html).strip():
        return ''
    raw = str(html).strip()
    if '<' not in raw and '>' not in raw:
        raw = _plain_text_to_html(raw)

    raw = _prepare_tinymce_html(raw)

    clean_kwargs = {
        'tags': ALLOWED_TAGS,
        'attributes': ALLOWED_ATTRIBUTES,
        'strip': True,
    }
    if CSS_SANITIZER is not None:
        clean_kwargs['css_sanitizer'] = CSS_SANITIZER

    cleaned = bleach.clean(raw, **clean_kwargs)

    if CSS_SANITIZER is None:
        cleaned = _sanitize_inline_styles_fallback(cleaned)

    cleaned = _filter_classes(cleaned)
    cleaned = _sanitize_bgcolor(cleaned)
    cleaned = _filter_iframes(cleaned)
    cleaned = _wrap_tables(cleaned)
    cleaned = _add_lazy_loading_to_images(cleaned)
    return cleaned
