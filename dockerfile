FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nano \
    libicu-dev \
    ffmpeg \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -m -d /home/appuser -s /bin/bash appuser

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY GUI/requirements.txt ./GUI/requirements.txt
RUN pip install --no-cache-dir -r GUI/requirements.txt

COPY . . 

RUN mkdir -p /app/Video /app/logs /app/data \
             /home/appuser/.config && \
    chown -R appuser:appuser /app /home/appuser && \
    chmod -R 755 /app /home/appuser

USER appuser

ENV PYTHONPATH="/app:${PYTHONPATH}" \
    HOME=/home/appuser

EXPOSE 8000

CMD ["sh", "-c", "python GUI/manage.py migrate --noinput && python GUI/manage.py runserver 0.0.0.0:8000"]