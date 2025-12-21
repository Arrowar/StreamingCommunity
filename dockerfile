FROM python:3.11-slim

# Installa le dipendenze di sistema incluso ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Crea utente e gruppo non-root con home directory
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -m -d /home/appuser -s /bin/bash appuser

WORKDIR /app

# Copia e installa i requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY GUI/requirements.txt ./GUI/requirements.txt
RUN pip install --no-cache-dir -r GUI/requirements.txt

# Copia tutto il codice dell'applicazione
COPY . . 

# Crea le directory necessarie e assegna i permessi
RUN mkdir -p /app/Video /app/logs /app/data \
             /home/appuser/.local/bin/binary \
             /home/appuser/.config && \
    chown -R appuser:appuser /app /home/appuser && \
    chmod -R 755 /app /home/appuser

# Cambia all'utente non-root
USER appuser

# Imposta le variabili d'ambiente
ENV PYTHONPATH="/app: ${PYTHONPATH}" \
    HOME=/home/appuser

EXPOSE 8000

CMD ["python", "GUI/manage.py", "runserver", "0.0.0.0:8000"]
