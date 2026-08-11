# Container for the Astro Classifier backend (FastAPI + TensorFlow models).
# Works on Hugging Face Spaces (Docker SDK) as well as any other
# Docker-based host (Railway, Fly.io, a VPS, etc.).

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer between builds.
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

# Copy the rest of the app (main.py, fits_utils.py, index.html, static/,
# the trained .keras models, class name files, etc.)
COPY . .

# Hugging Face Spaces expects the app to listen on this port when
# app_port is set to 8000 in the README.md metadata block.
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
