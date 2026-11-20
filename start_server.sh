#!/usr/bin/env bash
set -euo pipefail

PUBLIC_PORT="${PORT:-8501}"
STREAMLIT_INTERNAL_PORT=8502
PTT_INTERNAL_PORT=8765

# Generar configuración Nginx en puerto único (compatible con Railway, Render, Fly.io y Docker local)
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/default.conf <<EOF
server {
    listen ${PUBLIC_PORT};
    server_name _;
    client_max_body_size 30M;

    # Endpoint de captura de audio Push-to-Talk remoto (mismo origen HTTPS/HTTP)
    location /ptt/ {
        proxy_pass http://127.0.0.1:${PTT_INTERNAL_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }

    # Aplicación principal Streamlit + WebSockets
    location / {
        proxy_pass http://127.0.0.1:${STREAMLIT_INTERNAL_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }
}
EOF

# Iniciar Streamlit en puerto interno
streamlit run app.py \
    --server.port="${STREAMLIT_INTERNAL_PORT}" \
    --server.address=127.0.0.1 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false &
STREAMLIT_PID=$!

# Manejar señales de apagado limpio
cleanup() {
    kill -TERM "${STREAMLIT_PID}" 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT

# Ejecutar Nginx en primer plano
exec nginx -g "daemon off;"
