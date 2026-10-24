# syntax=docker/dockerfile:1
# AccessLoop in a container: the same engine, sandboxed Chromium and axe-core, on any machine with Docker.
#
#   docker build -t accessloop .
#   docker run --rm -p 127.0.0.1:8501:8501 -v accessloop-data:/data accessloop      # http://localhost:8501
#
# Or: docker compose up --build. Build without the optional AI packages: --build-arg WITH_AI=0

# ---- Stage 1: fetch axe-core exactly as pinned in package-lock.json (integrity-checked by npm ci) ----
FROM node:22-bookworm-slim AS axe
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund --omit=dev

# ---- Stage 2: the application ----
FROM python:3.12-slim-bookworm

ARG WITH_AI=1
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    ACCESSLOOP_HOME=/data/home \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Python packages (exact tested versions) and Chromium with its system libraries.
COPY requirements.txt requirements.lock requirements-ai.txt ./
RUN python -m pip install -r requirements.lock \
 && if [ "$WITH_AI" = "1" ]; then python -m pip install -r requirements-ai.txt; fi \
 && python -m playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*

# Run as an unprivileged user. Accounts, signing keys and page workspaces live on the /data volume.
RUN useradd --create-home --uid 10001 accessloop \
 && mkdir -p /data/home /data/workspaces \
 && chown -R accessloop:accessloop /data

COPY --chown=accessloop:accessloop . .
COPY --from=axe --chown=accessloop:accessloop /build/node_modules ./node_modules
RUN rm -rf .accessloop_workspaces && ln -s /data/workspaces .accessloop_workspaces

USER accessloop
VOLUME ["/data"]
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).status == 200 else 1)"

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
