"""Unit tests for get_kronos_forecast tool (mocked HTTP)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from tradingagents.agents.utils.kronos_forecast_tool import get_kronos_forecast


def test_skips_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("SIDECAR_BASE_URL", raising=False)
    monkeypatch.delenv("KRONOS_SIDECAR_URL", raising=False)
    monkeypatch.delenv("SIDECAR_JWT", raising=False)
    out = get_kronos_forecast.invoke({"symbol": "NVDA"})
    assert "unavailable" in out.lower()


def test_happy_path_mocked(monkeypatch) -> None:
    monkeypatch.setenv("SIDECAR_BASE_URL", "http://127.0.0.1:8765")
    monkeypatch.setenv("SIDECAR_JWT", "test-token")
    payload = {
        "ticker": "NVDA",
        "model_id": "NeoQuasar/Kronos-small",
        "last_close": 100.0,
        "pred_close": 101.0,
        "pred_pct_change": 1.0,
        "requested_pred_len": 5,
        "served_pred_len": 5,
        "horizon_capped": False,
        "horizon_note": "",
        "path_summary": "ok",
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    with patch("urllib.request.urlopen", return_value=mock_resp):
        out = get_kronos_forecast.invoke({"symbol": "nvda", "pred_len": 5})
    data = json.loads(out)
    assert data["ticker"] == "NVDA"
    assert data["served_pred_len"] == 5
    assert "not a trading recommendation" in data["note"].lower()
