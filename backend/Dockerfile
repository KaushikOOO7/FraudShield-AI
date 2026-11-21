FROM python:3.14.4-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# OpenCV's installed wheel requires these runtime shared libraries.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/constraints.txt /app/backend/
RUN python -m pip install --no-cache-dir -r backend/requirements.txt

COPY backend /app/backend
COPY scripts /app/scripts
RUN useradd --create-home --uid 1000 fraudshield && mkdir -p /app/data && chown fraudshield:fraudshield /app/data
USER fraudshield

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
