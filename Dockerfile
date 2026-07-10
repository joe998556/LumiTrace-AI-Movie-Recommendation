FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    WEB_CONCURRENCY=1 \
    LUMITRACE_VECTOR_FILE=/app/demo_index \
    LUMITRACE_TEXT_SEARCH=disabled \
    LUMITRACE_PRELOAD_INDEX=true \
    LUMITRACE_PREFER_LOCAL_INDEX=true \
    LUMITRACE_MIN_VOTE_COUNT=20 \
    LOCK_REMOTE_SEARCH_URL=true

WORKDIR /app

COPY requirements-demo.txt ./
RUN python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch \
    && python -m pip install --no-cache-dir -r requirements-demo.txt

COPY . .

EXPOSE 7860
CMD ["python", "tools/start_demo.py"]
