FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG INSTALL_TRAINING_DEPS=false
COPY training_requirements.txt .
RUN if [ "$INSTALL_TRAINING_DEPS" = "true" ]; then pip install --no-cache-dir -r training_requirements.txt; else echo "Skip training deps"; fi

COPY . .

RUN mkdir -p /app/uploads

EXPOSE 5000

CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "120"]
