FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libxml2-dev \
    libxslt1-dev

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "test_run.py"]
