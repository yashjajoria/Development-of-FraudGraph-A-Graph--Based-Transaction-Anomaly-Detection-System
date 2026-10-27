FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=web /web/dist frontend/dist
ENV APP_ENV=production PYTHONUNBUFFERED=1
WORKDIR /app/backend
EXPOSE 8000
# Required env: DATABASE_URL, JWT_SECRET, DEMO_PASSWORD, GROQ_API_KEY (or another provider's key)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
