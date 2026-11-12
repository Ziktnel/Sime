# Imagem única para o deploy: API FastAPI (porta interna 8000) + site Next.js (porta $PORT).
FROM node:22-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build && npm prune --omit=dev

FROM python:3.12-slim
COPY --from=web /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=web /app/frontend /app/frontend
COPY deploy/start.sh /app/start.sh
ENV PORT=10000 NODE_ENV=production
EXPOSE 10000
CMD ["sh", "/app/start.sh"]
