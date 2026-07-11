import httpx
import pytest
from app.gate.rest_client import GateRestClient

@pytest.mark.asyncio
async def test_gate_429_retry(settings):
    calls = 0
    def handler(request):
        nonlocal calls; calls += 1; return httpx.Response(429 if calls == 1 else 200, json=[])
    client = GateRestClient(settings, transport=httpx.MockTransport(handler)); result = await client.get_contracts(); await client.close(); assert result == []; assert calls == 2

