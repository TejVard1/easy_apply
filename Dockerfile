FROM python:3.11-slim

ARG INSTALL_FULL=0

WORKDIR /app
COPY . /app

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install --no-build-isolation -e . && \
    if [ "$INSTALL_FULL" = "1" ]; then \
      python -m pip install --no-build-isolation ".[full]" && \
      python -m playwright install --with-deps chromium; \
    fi

EXPOSE 8765
CMD ["python", "-m", "easy_apply", "serve", "--host", "0.0.0.0", "--port", "8765"]
