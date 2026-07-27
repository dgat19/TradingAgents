"""Optional Kronos path-forecast tool (HTTP to TradingAgentsSidecar).

Never imports torch. Enabled when ``KRONOS_SIDECAR_URL`` (or
``SIDECAR_BASE_URL``) and ``SIDECAR_JWT`` are set in the process env.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Annotated

from langchain_core.tools import tool


def _sidecar_config() -> tuple[str, str] | None:
    base = (
        os.environ.get("KRONOS_SIDECAR_URL")
        or os.environ.get("SIDECAR_BASE_URL")
        or ""
    ).rstrip("/")
    token = (os.environ.get("SIDECAR_JWT") or "").strip()
    if not base or not token:
        return None
    return base, token


@tool
def get_kronos_forecast(
    symbol: Annotated[str, "ticker symbol of the company"],
    pred_len: Annotated[int, "number of bars to forecast"] = 32,
    timeframe: Annotated[str, "bar interval: 1h or 1D"] = "1D",
) -> str:
    """Fetch a Kronos OHLCV path forecast from TradingAgentsSidecar.

    Research-only quantitative path — not a buy/sell recommendation.
    Returns a short JSON summary, or an explicit skip message when the
    Sidecar Kronos endpoint is not configured.
    """
    cfg = _sidecar_config()
    if cfg is None:
        return (
            "Kronos forecast unavailable: set SIDECAR_BASE_URL (or "
            "KRONOS_SIDECAR_URL) and SIDECAR_JWT to enable."
        )
    base, token = cfg
    q = urllib.parse.urlencode(
        {
            "pred_len": str(max(1, int(pred_len))),
            "timeframe": timeframe or "1D",
        }
    )
    url = f"{base}/api/analyst/{urllib.parse.quote(symbol.upper())}/forecast?{q}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return f"Kronos forecast request failed: {exc}"

    summary = {
        "ticker": body.get("ticker"),
        "model_id": body.get("model_id"),
        "last_close": body.get("last_close"),
        "pred_close": body.get("pred_close"),
        "pred_pct_change": body.get("pred_pct_change"),
        "requested_pred_len": body.get("requested_pred_len"),
        "served_pred_len": body.get("served_pred_len"),
        "horizon_capped": body.get("horizon_capped"),
        "horizon_note": body.get("horizon_note"),
        "path_summary": body.get("path_summary"),
        "note": "Research-only path forecast — not a trading recommendation.",
    }
    return json.dumps(summary, indent=2)
