FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY telemetry_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY telemetry_api/ ./telemetry_api/

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "telemetry_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
