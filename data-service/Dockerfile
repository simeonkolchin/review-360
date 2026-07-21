FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app /app/app
EXPOSE 8011
RUN mkdir -p /app/logs /app/openapi_spec && chmod -R 777 /app/logs /app/openapi_spec
CMD ["sh", "-c", "uvicorn app.app:app --host 0.0.0.0 --port ${DATA_SERVICE_PORT:-8011}"]
