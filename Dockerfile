FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt requirements-db.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-db.txt
RUN useradd --create-home appuser && chown appuser /app
COPY --chown=appuser:appuser app.py ./
COPY --chown=appuser:appuser agroshift ./agroshift
COPY --chown=appuser:appuser data ./data
COPY --chown=appuser:appuser static ./static
COPY --chown=appuser:appuser db ./db
COPY --chown=appuser:appuser scripts ./scripts
COPY --chown=appuser:appuser .streamlit ./.streamlit
USER appuser
HEALTHCHECK CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:'+os.environ['PORT']+'/_stcore/health', timeout=5)"
CMD ["sh", "-c", "exec python -m streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT"]
