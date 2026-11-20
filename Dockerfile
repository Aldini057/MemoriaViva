# MemoriaViva RISE - Dockerfile
FROM python:3.11-slim

# Evitar prompts y configurar buffers
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instalar dependencias del sistema requeridas para audio, fuentes, proxy y compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    libasound2-dev \
    libsndfile1 \
    ffmpeg \
    nginx \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .
RUN chmod +x /app/start_server.sh

# Exponer puerto único público (Nginx -> Streamlit + /ptt/*) y puerto PTT opcional
EXPOSE 8501 8765

# Healthcheck sobre el puerto público (compatible con $PORT en Railway/Render/Fly.io)
HEALTHCHECK CMD sh -c 'curl --fail http://localhost:${PORT:-8501}/_stcore/health || exit 1'

# Comando de arranque unificado
ENTRYPOINT ["/app/start_server.sh"]
