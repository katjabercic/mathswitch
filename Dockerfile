FROM python:3.12-slim

# Optional heavy dependencies. Pass --build-arg WITH_TORCH=false to leave out
# torch and accelerate (only the LLM categorizer needs them), and
# --build-arg WITH_SCISPACY_MODEL=false to leave out the ~700 MB scispaCy
# model (only Wikipedia keyword extraction during import_wikidata needs it).
ARG WITH_TORCH=true
ARG WITH_SCISPACY_MODEL=true

# gcc/g++ to compile some Python packages, git for lmfdb-lite (installed from git)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY web/requirements.txt requirements.txt

# torch gets its own layer, before the other requirements, so that it stays
# cached when they change. The CPU-only wheel avoids pulling several GB of
# CUDA libraries. The version is taken from requirements.txt.
RUN if [ "$WITH_TORCH" = "true" ]; then \
        pip install --no-cache-dir \
            --index-url https://download.pytorch.org/whl/cpu \
            "$(grep -E '^torch[~=<>]' requirements.txt | sed 's/ *#.*//')"; \
    fi

# Without torch, also drop accelerate, which depends on torch.
RUN if [ "$WITH_TORCH" = "true" ]; then \
        cp requirements.txt requirements.docker.txt; \
    else \
        grep -vE '^(torch|accelerate)[~=<>]' requirements.txt > requirements.docker.txt; \
    fi \
    && pip install --no-cache-dir gunicorn~=23.0 -r requirements.docker.txt

# Version is pinned to match the scispacy package in requirements.txt.
RUN if [ "$WITH_SCISPACY_MODEL" = "true" ]; then \
        pip install --no-cache-dir \
            https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz; \
    fi

COPY web/ .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
