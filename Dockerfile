FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi uvicorn \
    duckdb==1.1.3 \
    trino \
    clickhouse-connect \
    psycopg2-binary \
    sqlglot \
    requests \
    fsspec \
    s3fs

COPY router.py .

CMD ["uvicorn", "router:app", "--host", "0.0.0.0", "--port", "8000"]
