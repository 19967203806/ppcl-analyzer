from app.components import flowchart_viewer
from app.components.result_tabs import _visible_analysis_warnings
from app.components.sidebar_panel import _display_status


def test_graphviz_viewer_has_no_inline_export_toolbar(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        flowchart_viewer.components,
        "html",
        lambda html, **kwargs: captured.update(html=html, kwargs=kwargs),
    )

    flowchart_viewer._render_graphviz_iframe('digraph { a -> b }')

    html = captured["html"]
    assert 'data-export="svg"' not in html
    assert "graphviz.dot(code)" in html
    assert 'data-zoom="out"' in html
    assert 'data-zoom="reset"' in html
    assert 'data-zoom="in"' in html
    assert "window.installChartZoom" in html
    assert "flowchart-viewport" in html
    assert captured["kwargs"]["height"] == 700


def test_sequence_viewer_has_no_inline_export_toolbar(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        flowchart_viewer.components,
        "html",
        lambda html, **kwargs: captured.update(html=html, kwargs=kwargs),
    )

    class FileService:
        def get_sequence_chart_code(self, file_id):
            return "sequenceDiagram\nA->>B: Hello"

    flowchart_viewer.render_sequence_chart(FileService(), 1)

    html = captured["html"]
    assert "mermaid.render" in html
    assert 'data-export="svg"' not in html
    assert 'data-zoom="out"' in html
    assert 'data-zoom="reset"' in html
    assert 'data-zoom="in"' in html
    assert "window.installChartZoom" in html
    assert "sequence-chart-viewport" in html
    assert captured["kwargs"]["height"] == 700


def test_chart_zoom_bounds_step_and_reset():
    html = flowchart_viewer._zoomable_chart_markup("chart", "chart-error")

    assert "const minScale = 0.25" in html
    assert "const maxScale = 3" in html
    assert "const step = 0.25" in html
    assert "const fitScale = Math.min(" in html
    assert "const defaultScale = Math.max(minScale, Math.min(1, fitScale))" in html
    assert "let scale = defaultScale" in html
    assert "applyScale(scale - step)" in html
    assert "applyScale(scale + step)" in html
    assert ">Fit</button>" in html
    assert "applyScale(defaultScale, false)" in html
    assert "zoomOut.disabled = scale <= minScale" in html
    assert "toolbar.dataset.zoomReady = 'true'" in html
    assert "overflow: auto" in html


def test_sidebar_fallback_exports_browser_rendered_graphviz(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        flowchart_viewer.components,
        "html",
        lambda html, **kwargs: captured.update(html=html, kwargs=kwargs),
    )

    flowchart_viewer.render_browser_downloads(
        "digraph { a -> b }", "flowchart"
    )

    html = captured["html"]
    assert 'class="export-toolbar compact"' in html
    assert 'data-export="svg"' in html
    assert 'data-export="svg" title="Download SVG" disabled' in html
    assert 'data-export="png"' in html
    assert 'data-export="pdf"' in html
    assert "graphviz.dot" in html
    assert 'const baseFilename = "flowchart"' in html
    assert "dataset.exportReady = 'true'" in html
    assert "button.disabled = false" in html
    assert "toolbar.dataset.exportError = 'true'" in html
    assert captured["kwargs"]["height"] == 54


def test_sidebar_fallback_exports_browser_rendered_mermaid(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        flowchart_viewer.components,
        "html",
        lambda html, **kwargs: captured.update(html=html, kwargs=kwargs),
    )

    flowchart_viewer.render_browser_downloads(
        "sequenceDiagram\nA->>B: Hello", "sequence_chart"
    )

    html = captured["html"]
    assert "mermaid.render" in html
    assert 'const baseFilename = "sequence_chart"' in html
    assert "`${baseFilename}.svg`" in html
    assert "`${baseFilename}.png`" in html
    assert "`${baseFilename}.pdf`" in html
    assert "window.installBrowserExports" in html


def test_renderer_only_warnings_are_hidden_for_existing_records():
    message = (
        "flowchart PDF was not generated; DOT source is available\n"
        "sequence chart PDF was not generated; Mermaid source is available"
    )
    details = {
        "status": "completed_with_warnings",
        "error_message": message,
    }

    assert _visible_analysis_warnings(message) == []
    assert _display_status(details) == "completed"


def test_diagram_source_cannot_terminate_script_element(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        flowchart_viewer.components,
        "html",
        lambda html, **kwargs: captured.update(html=html),
    )
    payload = '</script><script>window.parent.document.body.innerHTML="owned"</script>'

    flowchart_viewer._render_graphviz_iframe(
        f'digraph {{ a [label="{payload}"] }}'
    )

    assert payload not in captured["html"]
    assert "\\u003c/script\\u003e" in captured["html"]
