import re
import textwrap


DOT_START_RE = re.compile(r"^\s*(?:strict\s+)?(?:di)?graph\b[^{]*\{", re.IGNORECASE | re.DOTALL)
LABEL_RE = re.compile(r'label="((?:[^"\\]|\\.)*)"', re.DOTALL)
GRAPH_SPACING_RE = re.compile(r"^(\s*)(nodesep|ranksep)\s*=\s*([0-9.]+)\s*;", re.IGNORECASE | re.MULTILINE)


def is_probably_dot(code: str) -> bool:
    stripped = code.strip()
    return bool(DOT_START_RE.match(stripped) and "}" in stripped)


def _wrap_label(match: re.Match[str]) -> str:
    raw_label = match.group(1)
    wrapped_parts = []
    for part in raw_label.split(r"\n"):
        clean_part = re.sub(r"\s+", " ", part).strip()
        if not clean_part:
            wrapped_parts.append("")
            continue
        wrapped_parts.extend(textwrap.wrap(clean_part, width=44, break_long_words=False) or [clean_part])
    # The captured label still carries DOT escapes (e.g. \" around an embedded
    # PPCL string). Only escape quotes that are not already escaped — a plain
    # ``.replace('"', '\\"')`` would turn a valid \" into a broken \\" that
    # closes the label early and makes Graphviz raise a syntax error.
    escaped = r"\n".join(
        re.sub(r'(?<!\\)"', r"\"", part) for part in wrapped_parts[:14]
    )
    return f'label="{escaped}"'


def _fix_overescaped_quotes(code: str) -> str:
    r"""Repair labels that double-escape inner quotes.

    A label may contain ``\\"`` (escaped backslash + closing quote) where the
    DOT grammar needs ``\"`` (escaped quote) — e.g. a PPCL ``LOOP(0,"%CHW.DP")``
    embedded in a label. The stray backslash closes the label early, leaving the
    next character (often ``%``) outside any string, so Graphviz aborts with
    ``syntax error ... near '%'`` and nothing renders. Collapsing ``\\"`` back to
    ``\"`` restores a parseable label. A real escaped backslash is followed by
    other text, not a quote, so it is left untouched.

    This repairs DOT already persisted with the broken escaping; ``_wrap_label``
    is what previously introduced it and no longer does.
    """
    return re.sub(r'\\\\"', r'\\"', code)


def normalize_dot_for_display(code: str) -> str:
    """Constrain generated DOT so Streamlit renders a readable chart."""
    normalized = _fix_overescaped_quotes(code.strip())
    def _normalized_spacing(name: str) -> str:
        return "nodesep=0.5" if name.lower() == "nodesep" else "ranksep=0.8"

    normalized = GRAPH_SPACING_RE.sub(
        lambda m: f"{m.group(1)}{_normalized_spacing(m.group(2))};",
        normalized,
    )
    normalized = re.sub(
        r"\b(nodesep|ranksep)\s*=\s*[0-9.]+",
        lambda m: _normalized_spacing(m.group(1)),
        normalized,
        flags=re.IGNORECASE,
    )
    if "nodesep" not in normalized:
        normalized = normalized.replace("{", "{\n    nodesep=0.5;", 1)
    if "ranksep" not in normalized:
        normalized = normalized.replace("{", "{\n    ranksep=0.8;", 1)
    if "rankdir" not in normalized:
        normalized = normalized.replace("{", "{\n    rankdir=TB;", 1)

    normalized = LABEL_RE.sub(_wrap_label, normalized)
    normalized = re.sub(r'fontsize\s*=\s*([0-9]+)', "fontsize=10", normalized)
    normalized = re.sub(r'edge \[([^\]]*)fontsize=11', r'edge [\1fontsize=9', normalized)
    return normalized + "\n"
