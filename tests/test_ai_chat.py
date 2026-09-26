from app.pages.ai_chat import DOC_OPTIONS


def test_chat_context_offers_all_core_analysis_artifacts():
    values = {value for _, value in DOC_OPTIONS}

    assert values == {
        "original_code",
        "cleaned_code",
        "logic_blocks",
        "data_points",
        "logic_doc",
        "flowchart_code",
        "sequence_chart_code",
    }
