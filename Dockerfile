FROM python:3.11-slim

WORKDIR /app

ENV TZ=America/Argentina/Buenos_Aires

# Install Python deps (tzdata included in requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Create empty credentials dir
RUN mkdir -p credentials

ENV PORT=8000
EXPOSE ${PORT}

CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
