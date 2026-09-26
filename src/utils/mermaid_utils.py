import re


def _sanitize_sequence_text(text: str) -> str:
    text = re.sub(r"<br\s*/?>", ", ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&", "and")
    text = text.replace("≤", "<=").replace("≥", ">=")
    text = text.replace("→", "->").replace("—", "-").replace("–", "-")
    text = text.replace(";", ",")
    text = re.sub(r"\.\s*,", ",", text)
    text = re.sub(r"(?<!\w)[$%]([A-Za-z_][\w.]*)", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_sequence_mermaid(code: str) -> str:
    """Normalize generated sequence diagrams for Mermaid 11 compatibility."""
    normalized_lines = []
    for line in code.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        participant = re.match(r"^(\s*participant\s+)(\w+)(?:\s+as\s+(.+?))?\s*$", line)
        if participant:
            indent, participant_id, display = participant.groups()
            display = (display or participant_id).strip().strip('"')
            display = _sanitize_sequence_text(display).replace('"', "'")
            normalized_lines.append(f'{indent}{participant_id} as "{display}"')
            continue

        if ":" in line and not line.lstrip().startswith("%%"):
            prefix, text = line.split(":", 1)
            text = _sanitize_sequence_text(text)
            line = f"{prefix}:{text}"
        else:
            block = re.match(r"^(\s*(?:alt|else|loop|opt|par|and|critical|break)\s+)(.+)$", line)
            if block:
                prefix, text = block.groups()
                line = f"{prefix}{_sanitize_sequence_text(text)}"
        normalized_lines.append(line)
    return "\n".join(normalized_lines).strip()
