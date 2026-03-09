FROM python:3.11-slim

WORKDIR /app

# Install tzdata for America/Buenos_Aires timezone
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=America/Buenos_Aires

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Create empty credentials dir (will use env vars in production)
RUN mkdir -p credentials

ENV PORT=8000
EXPOSE ${PORT}

CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
