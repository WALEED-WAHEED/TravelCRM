FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    python3-pip \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create directories for static and media files
RUN mkdir -p /app/staticfiles
RUN mkdir -p /app/media

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "travelcrm.wsgi:application", "--bind", "0.0.0.0:8000"]

