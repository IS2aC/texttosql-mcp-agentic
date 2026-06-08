FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt est à la racine de client/
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout client/ dans /app
COPY . .

# Le point d'entrée est web/app.py
WORKDIR /app/web

RUN mkdir -p system_prompts logs

EXPOSE 5050

CMD ["python", "app.py"]