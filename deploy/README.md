# Deployment (single Debian/Ubuntu host)

Reference setup used for the public demo: systemd runs the API and the UI as an
unprivileged `ppcl` user, and nginx exposes only the Streamlit UI on port 80.

```text
internet :80 -> nginx -> 127.0.0.1:8501 Streamlit -> 127.0.0.1:8000 FastAPI
```

1. Install system packages: `apt install nginx graphviz` and [uv](https://docs.astral.sh/uv/).
2. Create the service user and checkout:
   `useradd --system --home /opt/ppcl-analyzer --shell /usr/sbin/nologin ppcl`,
   clone the repository to `/opt/ppcl-analyzer`, then run `uv sync --python 3.10` there.
3. Copy `.env.example` to `.env`, set the model credentials, a strong
   `BOOTSTRAP_PASSWORD`, and `DAILY_ANALYSIS_LIMIT` / `DAILY_CHAT_LIMIT` for a public demo.
   Restrict it with `chmod 600 .env` and `chown -R ppcl:ppcl /opt/ppcl-analyzer`.
4. Install `ppcl-backend.service` and `ppcl-frontend.service` into `/etc/systemd/system/`,
   then `systemctl enable --now ppcl-backend ppcl-frontend`.
5. Install `nginx.conf` as `/etc/nginx/sites-available/ppcl-analyzer`, link it into
   `sites-enabled`, remove the default site, and `systemctl reload nginx`.

The Mermaid CLI is optional. Without it, sequence diagrams are still rendered in the
browser and runs are marked "completed with warnings" instead of producing a PDF.
