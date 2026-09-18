FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app
COPY . /app
RUN pip install --no-cache-dir . && chown -R app:app /app

USER app
EXPOSE 10000

# Render also checks /healthz. This works locally without curl in the image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '10000') + '/healthz', timeout=3)" || exit 1

CMD ["sh", "/app/start.sh"]
