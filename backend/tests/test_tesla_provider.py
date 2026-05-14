"""Replay tests — use fixture JSON, never hit real Tesla API."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services.providers.tesla import TeslaProvider, _infer_model, _infer_year, _miles_to_km

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
async def test_list_vehicles_replay() -> None:
    fixture = load("tesla_vehicles.json")

    mock_response = AsyncMock()
    mock_response.json.return_value = fixture
    mock_response.raise_for_status = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        provider = TeslaProvider(access_token="test-token")
        vehicles = await provider.list_vehicles()

    assert len(vehicles) == 1
    assert vehicles[0].vin == "5YJ3E1EA1PF000001"
    assert vehicles[0].display_name == "My Model 3"
    assert vehicles[0].provider_vehicle_id == "1234567890"


@pytest.mark.asyncio
async def test_get_vehicle_state_replay() -> None:
    fixture = load("tesla_vehicle_data.json")

    mock_response = AsyncMock()
    mock_response.json.return_value = fixture
    mock_response.raise_for_status = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        provider = TeslaProvider(access_token="test-token")
        state = await provider.get_vehicle_state("1234567890")

    assert state.battery_level == 72
    assert state.usable_battery_level == 71
    assert state.charging_state == "Disconnected"
    assert state.plugged_in is False
    assert state.latitude == pytest.approx(37.412374)
    assert state.odometer_km == pytest.approx(20041.7, rel=0.01)  # 12453.7 miles


def test_miles_to_km() -> None:
    assert _miles_to_km(100) == pytest.approx(160.93, rel=0.01)
    assert _miles_to_km(None) is None


def test_infer_model() -> None:
    assert _infer_model("5YJ3E1EA1PF000001") == "Model 3"
    assert _infer_model("5YJSA1E26MF000001") == "Model S"
    assert _infer_model("") is None


def test_infer_year() -> None:
    assert _infer_year("5YJ3E1EA1PF000001") == 2023
    assert _infer_year("5YJ3E1EA1NF000001") == 2022
    assert _infer_year("short") is None
