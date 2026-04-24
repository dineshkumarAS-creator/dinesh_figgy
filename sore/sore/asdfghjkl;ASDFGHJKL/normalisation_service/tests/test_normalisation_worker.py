import pytest
from unittest.mock import AsyncMock, MagicMock
from normalisation_service.normalisation_worker import NormalisationWorker


class TestNormalisationWorker:
    @pytest.fixture
    def worker(self):
        return NormalisationWorker()

    @pytest.mark.asyncio
    async def test_start_stop(self, worker):
        # Mock the consumer and producer
        worker.consumer = AsyncMock()
        worker.producer = AsyncMock()

        await worker.start()
        worker.consumer.start.assert_called_once()
        worker.producer.start.assert_called_once()

        await worker.stop()
        worker.consumer.stop.assert_called_once()
        worker.producer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_weather_message(self, worker):
        # Mock message
        message = MagicMock()
        message.topic = "weather"
        message.key = b"key"
        message.value = {
            "location": "Delhi",
            "timestamp": 1640995200000,
            "temperature_c": 25.0,
            "provider": "openweather"
        }

        # Mock consumer and producer
        worker.consumer = AsyncMock()
        worker.consumer.__aiter__ = AsyncMock(return_value=iter([message]))
        worker.producer = AsyncMock()

        # Run for one message
        async def mock_iter():
            yield message
            raise StopAsyncIteration

        worker.consumer.__aiter__ = mock_iter

        await worker.run()

        # Check that producer was called with normalised data
        worker.producer.send_and_wait.assert_called_once()
        call_args = worker.producer.send_and_wait.call_args
        assert call_args[0][0] == "weather_normalised"  # normalised topic
        normalised_data = call_args[0][2]  # value
        assert "normalised_temperature_c" in normalised_data

    @pytest.mark.asyncio
    async def test_process_aqi_message(self, worker):
        message = MagicMock()
        message.topic = "aqi"
        message.key = b"key"
        message.value = {
            "location": "Delhi",
            "timestamp": 1640995200000,
            "aqi_value": 100,
            "provider": "iqair"
        }

        worker.consumer = AsyncMock()
        worker.consumer.__aiter__ = AsyncMock(return_value=iter([message]))
        worker.producer = AsyncMock()

        async def mock_iter():
            yield message
            raise StopAsyncIteration

        worker.consumer.__aiter__ = mock_iter

        await worker.run()

        worker.producer.send_and_wait.assert_called_once()
        call_args = worker.producer.send_and_wait.call_args
        assert call_args[0][0] == "aqi_normalised"
        normalised_data = call_args[0][2]
        assert "normalised_aqi_us" in normalised_data

    @pytest.mark.asyncio
    async def test_process_telemetry_message(self, worker):
        message = MagicMock()
        message.topic = "worker_telemetry"
        message.key = b"key"
        message.value = {
            "worker_id": "worker_1",
            "event_type": "gps",
            "timestamp_utc": "2023-01-01T00:00:00Z",
            "lat": 28.6139,
            "lon": 77.2090
        }

        worker.consumer = AsyncMock()
        worker.consumer.__aiter__ = AsyncMock(return_value=iter([message]))
        worker.producer = AsyncMock()

        async def mock_iter():
            yield message
            raise StopAsyncIteration

        worker.consumer.__aiter__ = mock_iter

        await worker.run()

        worker.producer.send_and_wait.assert_called_once()
        call_args = worker.producer.send_and_wait.call_args
        assert call_args[0][0] == "telemetry_normalised"
        normalised_data = call_args[0][2]
        assert "normalised_lat" in normalised_data

    @pytest.mark.asyncio
    async def test_error_handling(self, worker):
        # Invalid message that causes normaliser to fail
        message = MagicMock()
        message.topic = "weather"
        message.key = b"key"
        message.value = {}  # Missing required fields

        worker.consumer = AsyncMock()
        worker.consumer.__aiter__ = AsyncMock(return_value=iter([message]))
        worker.producer = AsyncMock()

        async def mock_iter():
            yield message
            raise StopAsyncIteration

        worker.consumer.__aiter__ = mock_iter

        await worker.run()

        # Should not publish, error should be logged
        worker.producer.send_and_wait.assert_not_called()