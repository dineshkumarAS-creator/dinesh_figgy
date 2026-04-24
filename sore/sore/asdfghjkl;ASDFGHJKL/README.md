# FIGGY Layer 1 Kafka Infrastructure

Complete Apache Kafka setup for FIGGY's data ingestion pipeline.

## Architecture Overview

- **Topics**: weather, aqi, events, worker_telemetry + DLQs
- **Partition Strategy**:
  - `worker_telemetry`: 12 partitions because messages are keyed by `worker_id` for per-worker ordering. More partitions allow better consumer parallelism while maintaining order within each worker's stream.
  - Other topics: 3-6 partitions for balanced load.
- **Retention**:
  - Telemetry: 6h (high volume, short-lived)
  - Weather/AQI: 24h (daily data)
  - Events: 72h (longer window for analysis)
  - DLQs: 7d (debugging retention)

## Local Development Setup

1. **Start Kafka Infrastructure**:
   ```bash
   docker-compose up -d
   ```

2. **Create Topics**:
   ```bash
   python kafka/kafka_admin.py --bootstrap-servers localhost:9092
   ```

3. **Register Schemas**:
   ```bash
   python kafka/register_schemas.py
   ```

4. **Access Kafka UI**:
   - Open http://localhost:8090
   - View topics, schemas, and messages

## Services

- **Kafka**: localhost:9092
- **Schema Registry**: http://localhost:8081
- **Kafka UI**: http://localhost:8090
- **Zookeeper**: localhost:2181

## Usage

### Producers
```python
from kafka.base_producer import BaseKafkaProducer
from kafka.kafka_config import config

async with BaseKafkaProducer("weather", "kafka/weather.avsc", config) as producer:
    await producer.publish("key", {"location": "NYC", "temperature_c": 25.0})
```

### Consumers
```python
from kafka.base_consumer import BaseKafkaConsumer
from kafka.kafka_config import config

class MyConsumer(BaseKafkaConsumer):
    async def process(self, message):
        print(f"Processing: {message}")

async with MyConsumer("weather", "my-group", "kafka/weather.avsc", config) as consumer:
    await consumer.run()
```

## Dependencies

Install Python packages:
```bash
pip install aiokafka confluent-kafka prometheus-client structlog
```