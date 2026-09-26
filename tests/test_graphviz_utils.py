from src.utils.graphviz_utils import is_probably_dot, normalize_dot_for_display


def test_is_probably_dot_rejects_model_explanation():
    assert not is_probably_dot("Please provide the PPCL code first.")


def test_normalize_dot_limits_spacing_and_wraps_labels():
    dot = '''digraph G {
    nodesep=25;
    ranksep=45;
    a [label="This is a very long label that should be wrapped so Streamlit does not render an unreadable oversized graph node."];
}'''

    normalized = normalize_dot_for_display(dot)

    assert "nodesep=0.5;" in normalized
    assert "ranksep=0.8;" in normalized
    assert "This is a very long label that should be" in normalized
    assert r"\nwrapped so Streamlit" in normalized


def test_normalize_keeps_escaped_quotes_single_escaped():
    # A label with a correctly escaped inner quote (\") must not be turned into
    # a broken \\" that closes the label early and breaks Graphviz parsing.
    dot = 'digraph G {\n  a [label="03060 LOOP(0,\\"%CHW.DP\\",0)\\nPID control"];\n}'

    normalized = normalize_dot_for_display(dot)

    assert '\\\\"' not in normalized  # no double-escaped quote
    assert '\\"%CHW.DP\\"' in normalized  # quote stays singly escaped


def test_normalize_repairs_already_double_escaped_quotes():
    # DOT persisted with the old double-escaping bug should still render: the
    # stray backslash is dropped so the label parses again.
    dot = 'digraph G {\n  a [label="03060 LOOP(0,\\\\"%CHW.DP\\\\",0)"];\n}'

    normalized = normalize_dot_for_display(dot)

    assert '\\\\"' not in normalized
    assert '\\"%CHW.DP\\"' in normalized
