FROM python:3.13-slim
WORKDIR /app/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "psycopg[binary]>=3.1"
COPY backend/ /app/backend/
# the web dashboard (if present) is served at "/"
COPY web/ /app/web/
EXPOSE 8000
CMD ["uvicorn", "akeraten.main:app", "--host", "0.0.0.0", "--port", "8000"]
