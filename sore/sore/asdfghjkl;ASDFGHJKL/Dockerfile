FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model for NLP
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Default to govt_feed_connector
# Override with: docker run -e CONNECTOR=news_feed_connector.py image_name
# or: docker run -e CONNECTOR=aqi_connector.py image_name
ENV CONNECTOR=govt_feed_connector.py

# Health check for Kafka availability
HEALTH CHECK  --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('kafka', 9092), timeout=5)" || exit 1

CMD ["sh", "-c", "python -u ${CONNECTOR}"]

