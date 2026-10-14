# Use official Python runtime as a parent image
# Django==6.0.3 (requirements.txt) requires Python >=3.12 — this was
# 3.11 and silently unbuildable until Phase 11's docker-compose smoke
# test actually tried it.
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn

# Copy project
COPY . .

# Collect static files. Needs Django settings to import cleanly, which
# (by design — see travelcrm/settings.py's "fails closed" comment) raises
# ImproperlyConfigured without a real DJANGO_SECRET_KEY whenever DEBUG is
# False, and neither is available at build time. collectstatic never
# reads the key's value, so a placeholder scoped to just this layer is
# safe — unset immediately after so the real image doesn't carry it and
# a container run without a real key at runtime still fails closed as
# intended, rather than silently accepting this placeholder.
ENV DJANGO_SECRET_KEY=build-time-placeholder-unused-by-collectstatic
RUN python manage.py collectstatic --noinput
ENV DJANGO_SECRET_KEY=

# Ensure the app starts on port 8000
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "travelcrm.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2"]