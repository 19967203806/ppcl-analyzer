import json

import streamlit as st
import streamlit.components.v1 as components

from src.utils.graphviz_utils import is_probably_dot, normalize_dot_for_display
from src.utils.mermaid_utils import normalize_sequence_mermaid

from ..services.file_service import FileService
from ..state.session_manager import SessionManager


def _json_for_script(value: str) -> str:
    """Encode JSON without allowing HTML to terminate a script element."""
    return (
        json.dumps(value)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _zoomable_chart_markup(container_id: str, error_id: str) -> str:
    """Build a scrollable chart viewport with shared button-only zoom."""
    viewport_id = f"{container_id}-viewport"
    toolbar_id = f"{container_id}-zoom-toolbar"
    return f"""
        <style>
          html, body {{ margin: 0; }}
          .chart-zoom-toolbar {{
            align-items: center;
            background: rgba(255, 255, 255, 0.96);
            display: flex;
            gap: 6px;
            justify-content: flex-end;
            padding: 4px 8px;
          }}
          .chart-zoom-toolbar button {{
            background: #ffffff;
            border: 1px solid #c9ced6;
            border-radius: 6px;
            color: #31333f;
            cursor: pointer;
            font: 600 13px sans-serif;
            height: 30px;
            min-width: 34px;
            padding: 0 9px;
          }}
          .chart-zoom-toolbar button:hover {{ background: #f2f5f8; }}
          .chart-zoom-toolbar button:disabled {{
            cursor: not-allowed;
            opacity: 0.5;
          }}
          .chart-zoom-level {{ min-width: 58px !important; }}
          .chart-viewport {{
            height: 654px;
            overflow: auto;
            position: relative;
            width: 100%;
          }}
          .chart-canvas {{
            align-items: flex-start;
            box-sizing: border-box;
            display: flex;
            justify-content: center;
            min-height: 100%;
            min-width: 100%;
            padding: 8px;
            width: max-content;
          }}
          .chart-canvas svg {{
            flex: 0 0 auto;
            max-width: none !important;
            transition: width 120ms ease, height 120ms ease;
          }}
          #{error_id} {{
            color: #8b1e1e;
            margin: 8px;
            white-space: pre-wrap;
          }}
        </style>
        <div id="{toolbar_id}" class="chart-zoom-toolbar">
          <button type="button" data-zoom="out" title="Zoom out" aria-label="Zoom out" disabled>−</button>
          <button type="button" data-zoom="reset" class="chart-zoom-level" title="Reset zoom" aria-label="Reset zoom" disabled>Fit</button>
          <button type="button" data-zoom="in" title="Zoom in" aria-label="Zoom in" disabled>+</button>
        </div>
        <pre id="{error_id}" style="display:none;"></pre>
        <div id="{viewport_id}" class="chart-viewport">
          <div id="{container_id}" class="chart-canvas"></div>
        </div>
        <script>
          window.installChartZoom = function(svg) {{
            if (!svg) {{
              throw new Error('Rendered SVG was not found');
            }}
            const viewport = document.getElementById('{viewport_id}');
            const toolbar = document.getElementById('{toolbar_id}');
            const zoomOut = toolbar.querySelector('[data-zoom="out"]');
            const zoomReset = toolbar.querySelector('[data-zoom="reset"]');
            const zoomIn = toolbar.querySelector('[data-zoom="in"]');
            const viewBox = svg.viewBox && svg.viewBox.baseVal;
            const rect = svg.getBoundingClientRect();
            const naturalWidth = Math.max(
              1,
              (viewBox && viewBox.width) ||
              parseFloat(svg.getAttribute('width')) ||
              rect.width ||
              1200
            );
            const naturalHeight = Math.max(
              1,
              (viewBox && viewBox.height) ||
              parseFloat(svg.getAttribute('height')) ||
              rect.height ||
              800
            );
            const minScale = 0.25;
            const maxScale = 3;
            const step = 0.25;
            const availableWidth = Math.max(1, viewport.clientWidth - 16);
            const availableHeight = Math.max(1, viewport.clientHeight - 16);
            const fitScale = Math.min(
              availableWidth / naturalWidth,
              availableHeight / naturalHeight
            );
            const defaultScale = Math.max(minScale, Math.min(1, fitScale));
            let scale = defaultScale;

            svg.style.maxWidth = 'none';
            svg.style.flex = '0 0 auto';

            function applyScale(nextScale, preserveCenter = true) {{
              const previousScale = scale;
              const centerX = (viewport.scrollLeft + viewport.clientWidth / 2) /
                previousScale;
              const centerY = (viewport.scrollTop + viewport.clientHeight / 2) /
                previousScale;
              scale = Math.max(
                minScale,
                Math.min(maxScale, Math.round(nextScale * 100) / 100)
              );
              svg.style.width = `${{naturalWidth * scale}}px`;
              svg.style.height = `${{naturalHeight * scale}}px`;
              zoomReset.textContent = `${{Math.round(scale * 100)}}%`;
              zoomOut.disabled = scale <= minScale;
              zoomIn.disabled = scale >= maxScale;
              if (preserveCenter) {{
                requestAnimationFrame(() => {{
                  viewport.scrollLeft = centerX * scale - viewport.clientWidth / 2;
                  viewport.scrollTop = centerY * scale - viewport.clientHeight / 2;
                }});
              }}
            }}

            zoomOut.addEventListener('click', () => applyScale(scale - step));
            zoomIn.addEventListener('click', () => applyScale(scale + step));
            zoomReset.addEventListener(
              'click',
              () => applyScale(defaultScale, false)
            );
            zoomOut.disabled = false;
            zoomReset.disabled = false;
            zoomIn.disabled = false;
            applyScale(defaultScale, false);
            toolbar.dataset.zoomReady = 'true';
          }};
        </script>
    """


def _browser_export_markup(base_filename: str, *, compact: bool = False) -> str:
    """Build an in-iframe toolbar that exports the rendered SVG."""
    filename_json = _json_for_script(base_filename)
    toolbar_class = "export-toolbar compact" if compact else "export-toolbar"
    svg_label = "SVG" if compact else "Download SVG"
    png_label = "PNG" if compact else "Download PNG"
    pdf_label = "PDF" if compact else "Download PDF"
    return f"""
        <style>
          .export-toolbar {{
            align-items: center;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 0 0 12px;
          }}
          .export-toolbar button {{
            background: #ffffff;
            border: 1px solid #c9ced6;
            border-radius: 6px;
            color: #31333f;
            cursor: pointer;
            font: 600 13px sans-serif;
            padding: 7px 12px;
          }}
          .export-toolbar button:hover {{ background: #f2f5f8; }}
          .export-toolbar button:disabled {{
            cursor: wait;
            opacity: 0.65;
          }}
          .export-toolbar.compact {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin: 0;
            width: 100%;
          }}
          .export-toolbar.compact button {{
            font-size: 12px;
            padding: 6px 4px;
            width: 100%;
          }}
          .export-error {{
            color: #ff6b6b;
            font: 600 12px sans-serif;
            line-height: 32px;
          }}
          .export-hint {{
            color: #68707c;
            font: 12px sans-serif;
          }}
        </style>
        <div class="{toolbar_class}">
          <button type="button" data-export="svg" title="Download SVG" disabled>{svg_label}</button>
          <button type="button" data-export="png" title="Download PNG" disabled>{png_label}</button>
          <button type="button" data-export="pdf" title="Download PDF" disabled>{pdf_label}</button>
          {"" if compact else '<span class="export-hint">Exports the current browser-rendered view</span>'}
        </div>
        <script>
          window.installBrowserExports = function(svg, errorBox) {{
            if (!svg) {{
              throw new Error('Rendered SVG was not found');
            }}
            const baseFilename = {filename_json};

            function dimensions() {{
              const rect = svg.getBoundingClientRect();
              const viewBox = svg.viewBox && svg.viewBox.baseVal;
              return {{
                width: Math.max(1, Math.ceil(
                  (viewBox && viewBox.width) || rect.width ||
                  parseFloat(svg.getAttribute('width')) || 1200
                )),
                height: Math.max(1, Math.ceil(
                  (viewBox && viewBox.height) || rect.height ||
                  parseFloat(svg.getAttribute('height')) || 800
                )),
              }};
            }}

            function serializeSvg() {{
              const size = dimensions();
              const clone = svg.cloneNode(true);
              clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
              clone.setAttribute('width', size.width);
              clone.setAttribute('height', size.height);
              return {{
                ...size,
                text: new XMLSerializer().serializeToString(clone),
              }};
            }}

            function downloadBlob(blob, filename) {{
              const url = URL.createObjectURL(blob);
              const link = document.createElement('a');
              link.href = url;
              link.download = filename;
              document.body.appendChild(link);
              link.click();
              link.remove();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            }}

            async function renderPng(requestedScale = 2) {{
              const source = serializeSvg();
              const maxPixels = 24000000;
              const maxDimension = 8192;
              const safeScale = Math.max(0.1, Math.min(
                requestedScale,
                maxDimension / source.width,
                maxDimension / source.height,
                Math.sqrt(maxPixels / (source.width * source.height))
              ));
              const canvas = document.createElement('canvas');
              canvas.width = Math.max(1, Math.round(source.width * safeScale));
              canvas.height = Math.max(1, Math.round(source.height * safeScale));
              const context = canvas.getContext('2d');
              context.fillStyle = '#ffffff';
              context.fillRect(0, 0, canvas.width, canvas.height);

              const image = new Image();
              const svgUrl = URL.createObjectURL(
                new Blob([source.text], {{ type: 'image/svg+xml;charset=utf-8' }})
              );
              try {{
                await new Promise((resolve, reject) => {{
                  image.onload = resolve;
                  image.onerror = () => reject(new Error('SVG could not be rasterized'));
                  image.src = svgUrl;
                }});
                context.drawImage(image, 0, 0, canvas.width, canvas.height);
              }} finally {{
                URL.revokeObjectURL(svgUrl);
              }}
              return {{
                dataUrl: canvas.toDataURL('image/png'),
                width: canvas.width,
                height: canvas.height,
              }};
            }}

            async function run(button, action) {{
              const originalLabel = button.textContent;
              button.disabled = true;
              button.textContent = 'Preparing…';
              try {{
                await action();
              }} catch (error) {{
                errorBox.style.display = 'block';
                errorBox.textContent = `Export failed: ${{error.message}}`;
              }} finally {{
                button.disabled = false;
                button.textContent = originalLabel;
              }}
            }}

            document.querySelector('[data-export="svg"]').addEventListener(
              'click',
              (event) => run(event.currentTarget, async () => {{
                const source = serializeSvg();
                downloadBlob(
                  new Blob([source.text], {{ type: 'image/svg+xml;charset=utf-8' }}),
                  `${{baseFilename}}.svg`
                );
              }})
            );
            document.querySelector('[data-export="png"]').addEventListener(
              'click',
              (event) => run(event.currentTarget, async () => {{
                const png = await renderPng(2);
                const response = await fetch(png.dataUrl);
                downloadBlob(await response.blob(), `${{baseFilename}}.png`);
              }})
            );
            document.querySelector('[data-export="pdf"]').addEventListener(
              'click',
              (event) => run(event.currentTarget, async () => {{
                const png = await renderPng(2);
                const {{ jsPDF }} = await import(
                  'https://cdn.jsdelivr.net/npm/jspdf@2.5.2/+esm'
                );
                const pdf = new jsPDF({{
                  orientation: png.width >= png.height ? 'landscape' : 'portrait',
                  unit: 'px',
                  format: [png.width, png.height],
                  hotfixes: ['px_scaling'],
                }});
                const pageWidth = pdf.internal.pageSize.getWidth();
                const pageHeight = pdf.internal.pageSize.getHeight();
                pdf.addImage(
                  png.dataUrl, 'PNG', 0, 0, pageWidth, pageHeight,
                  undefined, 'FAST'
                );
                pdf.save(`${{baseFilename}}.pdf`);
              }})
            );
            const toolbar = document.querySelector('.export-toolbar');
            toolbar.querySelectorAll('[data-export]').forEach((button) => {{
              button.disabled = false;
            }});
            toolbar.dataset.exportReady = 'true';
          }};
        </script>
    """


def _show_missing_artifact(label: str) -> None:
    file_details = st.session_state.get(SessionManager.FILE_DETAILS) or {}
    status = file_details.get("status", "unknown")
    error_message = file_details.get("error_message")
    st.warning(f"{label} was not generated for this analysis run. Status: {status}.")
    if error_message:
        with st.expander("Show analysis details"):
            st.text(error_message)


def _render_graphviz_iframe(dot_code: str) -> None:
    """Render Graphviz DOT inside an isolated iframe.

    Rendering through ``components.html`` (an iframe) instead of
    ``st.graphviz_chart`` keeps the d3-graphviz DOM manipulation out of
    Streamlit's React tree. Otherwise, switching away from this view makes
    React call ``removeChild`` on a node the graphviz library already moved,
    raising ``NotFoundError: ... is not a child of this node``.
    """
    code_json = _json_for_script(dot_code)
    viewer_markup = _zoomable_chart_markup("flowchart", "flowchart-error")
    components.html(
        f"""
        {viewer_markup}
        <script type="module">
          import {{ Graphviz }} from 'https://cdn.jsdelivr.net/npm/@hpcc-js/wasm@2.16.0/dist/graphviz.js';
          const code = {code_json};
          try {{
            const graphviz = await Graphviz.load();
            document.getElementById('flowchart').innerHTML = graphviz.dot(code);
            window.installChartZoom(
              document.querySelector('#flowchart svg')
            );
          }} catch (error) {{
            const errorBox = document.getElementById('flowchart-error');
            errorBox.style.display = 'block';
            errorBox.textContent = `Graphviz render failed: ${{error.message}}\\n\\n${{code}}`;
            document.getElementById('flowchart-viewport').style.display = 'none';
            document.getElementById('flowchart-zoom-toolbar').style.display = 'none';
          }}
        </script>
        """,
        height=700,
        scrolling=False,
    )


def render_flowchart(file_service: FileService, file_id: int):
    """render flowchart"""
    code = file_service.get_flowchart_code(file_id)

    if code:
        if not code.strip():
            st.warning("Flowchart DOT source is empty")
            return
        if not is_probably_dot(code):
            st.error("Flowchart source is not valid Graphviz DOT. Please rerun the analysis.")
            with st.expander("Show invalid flowchart source"):
                st.code(code, language="text")
            return
        code = normalize_dot_for_display(code)
        _render_graphviz_iframe(code)
    else:
        _show_missing_artifact("Flowchart")

def render_sequence_chart(file_service: FileService, file_id: int):
    """render sequence chart"""
    code = file_service.get_sequence_chart_code(file_id)
    if code:
        if not code.strip():
            st.warning("Sequence chart mermaid source is empty")
            return
        normalized_code = normalize_sequence_mermaid(code)
        code_json = _json_for_script(normalized_code)
        viewer_markup = _zoomable_chart_markup(
            "sequence-chart", "sequence-error"
        )
        components.html(
            f"""
            {viewer_markup}
            <script type="module">
              import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
              mermaid.initialize({{ startOnLoad: false, securityLevel: 'strict' }});
              const code = {code_json};
              try {{
                const result = await mermaid.render('sequence-chart-svg', code);
                document.getElementById('sequence-chart').innerHTML = result.svg;
                window.installChartZoom(
                  document.querySelector('#sequence-chart svg')
                );
              }} catch (error) {{
                const errorBox = document.getElementById('sequence-error');
                errorBox.style.display = 'block';
                errorBox.textContent = `Mermaid render failed: ${{error.message}}\\n\\n${{code}}`;
                document.getElementById('sequence-chart-viewport').style.display = 'none';
                document.getElementById('sequence-chart-zoom-toolbar').style.display = 'none';
              }}
            </script>
            """,
            height=700,
            scrolling=False,
        )
    else:
        _show_missing_artifact("Sequence chart")


def render_browser_downloads(code: str, chart_type: str) -> None:
    """Render a hidden browser chart and expose compact sidebar downloads."""
    is_sequence = chart_type == "sequence_chart"
    base_filename = "sequence_chart" if is_sequence else "flowchart"
    normalized_code = (
        normalize_sequence_mermaid(code)
        if is_sequence
        else normalize_dot_for_display(code)
    )
    code_json = _json_for_script(normalized_code)
    export_markup = _browser_export_markup(base_filename, compact=True)
    if is_sequence:
        module_import = (
            "import mermaid from "
            "'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';"
        )
        renderer = f"""
          mermaid.initialize({{ startOnLoad: false, securityLevel: 'strict' }});
          const result = await mermaid.render('sidebar-sequence-export-svg', {code_json});
          document.getElementById('browser-export-render').innerHTML = result.svg;
        """
    else:
        module_import = (
            "import { Graphviz } from "
            "'https://cdn.jsdelivr.net/npm/@hpcc-js/wasm@2.16.0/dist/graphviz.js';"
        )
        renderer = f"""
          const graphviz = await Graphviz.load();
          document.getElementById('browser-export-render').innerHTML =
            graphviz.dot({code_json});
        """

    components.html(
        f"""
        {export_markup}
        <div id="browser-export-render" style="position:absolute;left:-100000px;top:0;"></div>
        <pre id="browser-export-error" style="display:none;white-space:pre-wrap;color:#ff6b6b;font-size:12px;"></pre>
        <script type="module">
          {module_import}
          try {{
            {renderer}
            window.installBrowserExports(
              document.querySelector('#browser-export-render svg'),
              document.getElementById('browser-export-error')
            );
          }} catch (error) {{
            const errorBox = document.getElementById('browser-export-error');
            errorBox.textContent = `Browser export unavailable: ${{error.message}}`;
            const toolbar = document.querySelector('.export-toolbar');
            const status = document.createElement('span');
            status.className = 'export-error';
            status.textContent = 'Browser export unavailable';
            toolbar.replaceChildren(status);
            toolbar.dataset.exportError = 'true';
          }}
        </script>
        """,
        height=54,
        scrolling=False,
    )
