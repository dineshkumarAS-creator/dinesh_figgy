import pytest
from unittest.mock import AsyncMock, patch
from ..clients.osrm_client import OsrmClient

@pytest.mark.asyncio
async def test_osrm_match_success():
    redis = AsyncMock()
    client = OsrmClient('localhost:5000')
    client.redis = redis
    client.client = AsyncMock()

    # Mock response
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {'matchings': [{'confidence': 0.9}]}
    client.client.get.return_value = mock_resp

    score = await client.match_road([(77.0, 28.0), (77.01, 28.01)])
    assert score == 0.9

@pytest.mark.asyncio
async def test_osrm_timeout():
    redis = AsyncMock()
    client = OsrmClient('localhost:5000')
    client.redis = redis
    client.client = AsyncMock()
    client.client.get.side_effect = Exception("Timeout")

    score = await client.match_road([(77.0, 28.0)])
    assert score == -1.0