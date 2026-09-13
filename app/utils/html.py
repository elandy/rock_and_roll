import html
import re

import bleach


_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)


def clean_html(value: str | None) -> str | None:
    if value is None:
        return None

    value = _SCRIPT_STYLE_RE.sub("", value)

    cleaned = bleach.clean(
        value,
        tags=[],
        attributes={},
        strip=True,
    )
    cleaned = html.unescape(cleaned)
    cleaned = " ".join(cleaned.split())

    return cleaned or None