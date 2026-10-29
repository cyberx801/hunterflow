# syntax=docker/dockerfile:1
# HunterFlow backend (API + worker share this image)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv is installed from PyPI (keeps the build independent of ghcr.io availability).
RUN pip install --no-cache-dir "uv==0.13.3"

# --- Tool stage: pinned ProjectDiscovery binaries with recorded checksums ---
FROM base AS tools
WORKDIR /opt/tools
COPY integrations/tools.lock /opt/tools.lock
RUN set -eux; \
    curl -fsSL -o subfinder.zip "https://github.com/projectdiscovery/subfinder/releases/download/v2.6.6/subfinder_2.6.6_linux_amd64.zip" \
    && echo "6fda32fe1f5750e63fa07c112b1b615d033e425c6dc6659ed8ec61035eb8eba2  subfinder.zip" | sha256sum -c - \
    && unzip -o subfinder.zip subfinder && chmod +x subfinder && rm subfinder.zip; \
    curl -fsSL -o httpx.zip "https://github.com/projectdiscovery/httpx/releases/download/v1.6.9/httpx_1.6.9_linux_amd64.zip" \
    && echo "c8d36461b5d736e88c3f9104fed15f2112eb7263dbda35fd08aa5a771bddfb5f  httpx.zip" | sha256sum -c - \
    && unzip -o httpx.zip httpx && chmod +x httpx && rm httpx.zip; \
    curl -fsSL -o katana.zip "https://github.com/projectdiscovery/katana/releases/download/v1.1.2/katana_1.1.2_linux_amd64.zip" \
    && echo "710205030c3d07a23d86fe11dac595a3c681ab5fa8daad679c752cbfd4ee0425  katana.zip" | sha256sum -c - \
    && unzip -o katana.zip katana && chmod +x katana && rm katana.zip; \
    curl -fsSL -o nuclei.zip "https://github.com/projectdiscovery/nuclei/releases/download/v3.3.7/nuclei_3.3.7_linux_amd64.zip" \
    && echo "725ef892fcffd1b03ad4f0874942fc4b623c0419b6b6c6c91fe4a5a65671f77c  nuclei.zip" | sha256sum -c - \
    && unzip -o nuclei.zip nuclei && chmod +x nuclei && rm nuclei.zip; \
    curl -fsSL -o dnsx.zip "https://github.com/projectdiscovery/dnsx/releases/download/v1.3.1/dnsx_1.3.1_linux_amd64.zip" \
    && echo "438b964653056dd51dcfe614b1a16f8bced3cc48a1d27bc07cc6fdf2ef2a9533  dnsx.zip" | sha256sum -c - \
    && unzip -o dnsx.zip dnsx && chmod +x dnsx && rm dnsx.zip; \
    curl -fsSL -o gau.tar.gz "https://github.com/lc/gau/releases/download/v2.2.4/gau_2.2.4_linux_amd64.tar.gz" \
    && echo "10e2e248c37cafb0be3f6d2931125296b95cd4186066d596d47fa417237529a9  gau.tar.gz" | sha256sum -c - \
    && tar -xzf gau.tar.gz gau && chmod +x gau && rm gau.tar.gz; \
    ls -la /opt/tools

# --- App stage ---
FROM base AS app
WORKDIR /srv/hunterflow
ENV UV_PROJECT_ENVIRONMENT=/venv

# Optional screenshot support: set WITH_SCREENSHOTS=1 at build time.
ARG WITH_SCREENSHOTS=0
RUN if [ "$WITH_SCREENSHOTS" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends chromium fonts-liberation \
      && rm -rf /var/lib/apt/lists/*; \
    fi

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

COPY --from=tools /opt/tools /usr/local/bin/

RUN useradd -m -u 10001 hunterflow
RUN mkdir -p /srv/hunterflow/data/evidence /srv/hunterflow/data/runs \
    && chown -R hunterflow:hunterflow /srv/hunterflow
USER hunterflow

EXPOSE 8000

COPY docker-entrypoint.sh /usr/local/bin/hf-entrypoint
CMD ["hf-entrypoint"]
