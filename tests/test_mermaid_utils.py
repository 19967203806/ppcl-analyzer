from src.utils.mermaid_utils import normalize_sequence_mermaid


def test_normalize_sequence_mermaid_sanitizes_note_text_and_participants():
    mermaid = '''sequenceDiagram
    participant SI as "Safety & Interlocks"
    alt %TEMP ≤ 20
        Note right of SI: Sets $PLANT.EN & %PLANT.ALM → HOLD
    end'''

    normalized = normalize_sequence_mermaid(mermaid)

    assert 'participant SI as "Safety and Interlocks"' in normalized
    assert "alt TEMP <= 20" in normalized
    assert "Sets PLANT.EN and PLANT.ALM -> HOLD" in normalized


def test_normalize_sequence_mermaid_removes_statement_breaking_semicolons():
    mermaid = '''sequenceDiagram
    participant SS as System Setup
    participant MC as Main Control
    Note over SS: Initializes thresholds.; Blocks: LB-01
    SS->>MC: GOSUB 00200–00430'''

    normalized = normalize_sequence_mermaid(mermaid)

    assert "thresholds, Blocks: LB-01" in normalized
    assert "00200-00430" in normalized
    assert ";" not in normalized
