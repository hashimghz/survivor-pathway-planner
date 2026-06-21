FROM python:3.12-slim

# uv from the official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install deps in a cacheable layer
COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync --no-dev

# App code (data/raw, models, engine, app, scripts, etc.)
COPY . .

# Precompute the L1 skill-embedding cache (downloads the ~130 MB model once,
# writes data/processed/skill_embeddings.npz). Baking it in here means the app
# doesn't try to build it at first request.
RUN uv run python engine/build_skill_corpus.py

EXPOSE 8501

# Streamlit on all interfaces, no telemetry, no file watcher
ENV STREAMLIT_SERVER_FILE_WATCHER_TYPE=none \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["uv", "run", "streamlit", "run", "app/Home.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]