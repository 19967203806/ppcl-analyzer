# PPCL Code Analysis

PPCL Code Analysis is a local engineering application for reviewing building-control programs. It combines a Streamlit interface with a FastAPI backend and produces model-assisted logic summaries, data-point inventories, Graphviz flowcharts, Mermaid sequence diagrams, and technical documentation.

This is an independent demonstration project. It is not affiliated with or endorsed by any building-automation vendor. The files in `examples/` are synthetic and do not come from a real facility or production control system.

## What It Does

- Authenticates local users with bearer tokens and keeps uploaded files separated by owner.
- Accepts `.ppcl`, `.pcl`, and `.txt` source files up to 10 MB.
- Stores the original input, a cleaned copy, run status, input hash, model provider, token usage, warnings, and generated artifacts.
- Uses LangGraph to run data-point, documentation, flowchart, and sequence-chart tasks after the initial logic-block analysis.
- Validates and normalizes diagram source before rendering.
- Shows failed and partially completed analyses explicitly.
- Provides a chat view that answers from the selected file artifacts and stored conversation history.
- Supports comments, previews, and downloads for generated artifacts.

## Architecture

```text
Streamlit frontend (:8501)
        |
        | HTTP with bearer token
        v
FastAPI backend (:8000)
        |
        +-- LangChain model interface
        +-- LangGraph analysis and QA workflows
        +-- SQLModel + SQLite metadata and comments
        +-- local output and log files
```

The upload request waits for the analysis to finish. Model calls run through a worker thread so the event loop is not blocked, while independent artifact tasks run concurrently inside the analysis graph. There is no background job queue in the current implementation.

## Requirements

- Python 3.10 or newer
- `uv`, or standard `venv` and `pip`
- Credentials for a Qwen-compatible OpenAI endpoint or Azure OpenAI
- Graphviz `dot` for server-generated flowchart PDFs
- Mermaid CLI `mmdc` for server-generated sequence-chart PDFs

On macOS, the optional diagram renderers can be installed with:

```bash
brew install graphviz
npm install -g @mermaid-js/mermaid-cli
```

If a renderer is unavailable, the application keeps valid diagram source where possible and marks the run as completed with warnings.

## Setup

Using `uv`:

```bash
uv sync --extra dev
```

Using standard Python tooling:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Copy the configuration template:

```bash
cp .env.example .env
```

Configure one model provider. The template includes this local demonstration account:

```dotenv
MODEL_PROVIDER=qwen
MODEL_NAME=qwen-plus
OPENAI_API_KEY=<provider-api-key>
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

BOOTSTRAP_USERNAME=admin
BOOTSTRAP_PASSWORD=ppcl-local-admin-2026
```

Azure OpenAI can be configured instead with the `AZURE_*` values documented in `.env.example`. Change the demonstration password before any shared or network-accessible deployment. Bootstrap credentials create the configured username if it does not exist; they do not overwrite an existing account's password.

## Run Locally

Start the API:

```bash
uv run python src_main.py
```

Start the Streamlit interface in another terminal:

```bash
uv run streamlit run app_main.py
```

Virtual-environment equivalents:

```bash
.venv/bin/python src_main.py
.venv/bin/streamlit run app_main.py
```

Open:

- Streamlit: <http://localhost:8501>
- API health: <http://localhost:8000/health>
- API documentation: <http://localhost:8000/docs>

Use `BACKEND_URL` in `.env` when the Streamlit process should call an API at another address.

## Synthetic Examples

- `examples/minimal_demo.ppcl` is a short smoke-test input.
- `examples/synthetic_chiller_plant_demo.ppcl` exercises branches, subroutines, alarms, interlocks, timers, and equipment commands.

Use only source files that you are authorized to process.

## Data and Privacy

- Uploaded source and generated artifacts are stored under `output/`.
- Comments and metadata are stored in `wiki.db`; run logs are stored under `logs/`.
- These runtime paths and `.env` are excluded by `.gitignore`.
- Source code and selected artifacts are sent to the model provider configured in `.env`.
- LangSmith tracing is disabled unless `LANGSMITH_TRACING=true` is set explicitly.
- Browser diagram previews currently download JavaScript packages from jsDelivr. A fully offline deployment must self-host those assets.

Do not upload confidential production code unless the selected model provider and deployment environment are approved for that data.

## Accuracy Boundaries

- The deterministic cleaner removes blank lines and lines whose seventh character is `C`; it is not a complete PPCL parser.
- Logic blocks, data points, documentation, and diagram source are model-generated and require engineering review.
- Successful DOT or Mermaid rendering proves diagram syntax, not control-logic correctness.
- Chat context is built directly from selected source and generated artifacts; it is not vector retrieval.

Generated output must not be used as the sole basis for operating or modifying a live control system.

## Verification

```bash
python3 -m compileall -q app src tests app_main.py src_main.py
python3 -m pytest -q
python3 -m pip check
```

On environments where pytest's terminal-capture plugin conflicts with the local Python build, use:

```bash
python3 -m pytest -p no:capture -q
```

## Current Limitations

- Analysis runs inside the upload request rather than a durable background queue.
- SQLite and local files are intended for local use or small controlled deployments.
- The application has no self-service registration, password reset, rate limiting, or production identity integration.
- The documented `admin` account is only a local demonstration credential and must not be used for a shared deployment.
- Internet-facing deployment requires TLS, access controls, backups, secret management, and a production database/storage design.
- Reliable graph topology ultimately requires a structured parser instead of model-authored diagrams alone.

See `ROADMAP.md` for the engineering roadmap and `docs/PUBLIC_RELEASE_CHECKLIST.md` before publishing.

## License

Released under the MIT License. See [LICENSE](LICENSE).
