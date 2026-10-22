FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PULSEIQ_DB_PATH=/data/pulseiq.duckdb

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY app.py etl.py ./
COPY pulseiq ./pulseiq
COPY pages ./pages
COPY scripts ./scripts
COPY 03_Data/csv ./03_Data/csv
COPY docs ./docs

EXPOSE 8501 8000
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
