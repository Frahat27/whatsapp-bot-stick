FROM python:3.11-slim

WORKDIR /app

# Install Python deps (asyncpg has pre-built wheels, no gcc needed)
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
