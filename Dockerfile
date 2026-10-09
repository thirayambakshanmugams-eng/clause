FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for spaCy, PDF processing, and OCR
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port (Railway uses dynamic PORT env var)
EXPOSE 8080

# Start with Gunicorn — binds to $PORT (Railway) or 8080 (other platforms)
CMD gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 2 --threads 4 --timeout 300 --graceful-timeout 30 'app:create_app()'
