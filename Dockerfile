FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt requirements-db.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-db.txt
RUN useradd --create-home appuser && chown appuser /app
COPY --chown=appuser:appuser agroshift ./agroshift
COPY --chown=appuser:appuser api ./api
COPY --chown=appuser:appuser config ./config
COPY --chown=appuser:appuser data ./data
COPY --chown=appuser:appuser db ./db
COPY --chown=appuser:appuser scripts ./scripts
USER appuser
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health', timeout=5)"
CMD ["sh", "-c", "exec uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
