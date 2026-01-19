FROM python:3.12-slim

LABEL maintainer="TrueNAS Password Manager"
LABEL description="Self-service password change portal for TrueNAS users"

# Set working directory
WORKDIR /app

# Install system dependencies for pysmb
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY run.py .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Environment variables (can be overridden)
ENV FLASK_ENV=production
ENV TRUENAS_HOST=localhost
ENV TRUENAS_PORT=443
ENV TRUENAS_USE_SSL=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/login')" || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app:create_app()"]
