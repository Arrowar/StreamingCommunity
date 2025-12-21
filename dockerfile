FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Crea un utente non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY GUI/requirements.txt ./GUI/requirements.txt
RUN pip install --no-cache-dir -r GUI/requirements.txt

COPY . .

# Assegna i permessi corretti all'utente non-root
RUN chown -R appuser:appuser /app

# Cambia all'utente non-root
USER appuser

ENV PYTHONPATH="/app:${PYTHONPATH}"

EXPOSE 8000

CMD ["python", "GUI/manage.py", "runserver", "0.0.0.0:8000"]
