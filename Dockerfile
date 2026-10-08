FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AMAN_ENVIRONMENT=staging \
    AMAN_PORT=8000

RUN groupadd --system --gid 10001 aman \
    && useradd --system --uid 10001 --gid aman --home-dir /home/aman --create-home aman

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/backend/requirements.txt

COPY --chown=aman:aman backend/ /app/backend/
COPY --chown=aman:aman schemas/ /app/schemas/
COPY --chown=aman:aman admin.html index.html aman-cmp.js aman-scanner.js demo-site.html scanner-tool.html /app/console/
COPY --chown=aman:aman demo-tags/ /app/console/demo-tags/
COPY --chown=aman:aman ops/container/entrypoint.sh /usr/local/bin/aman-entrypoint

RUN chmod 0555 /usr/local/bin/aman-entrypoint

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD-SHELL python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('AMAN_PORT', '8000') + '/health/ready', timeout=3)"

ENTRYPOINT ["/usr/local/bin/aman-entrypoint"]
CMD ["serve"]
