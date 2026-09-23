"""Market price service for Agmarknet data."""
from datetime import date, datetime, timedelta, timezone

import requests

import config


def _record_value(record: dict, *names: str):
    for name in names:
        if name in record and record[name] not in (None, ""):
            return record[name]
    normalized = {str(key).lower().replace("_", ""): value for key, value in record.items()}
    for name in names:
        value = normalized.get(name.lower().replace("_", ""))
        if value not in (None, ""):
            return value
    return None


def _matches_market(record: dict, commodity: str, state: str) -> bool:
    """Match user-friendly crop names such as Paddy to Agmarknet variants."""
    record_state = str(_record_value(record, "State", "state") or "").strip().casefold()
    record_commodity = str(_record_value(record, "Commodity", "commodity") or "").strip().casefold()
    requested_state = state.strip().casefold()
    requested_commodity = commodity.strip().casefold()
    commodity_aliases = {
        "chilli": {"chilli", "chili", "green chilli", "green chili"},
        "chili": {"chilli", "chili", "green chilli", "green chili"},
    }
    requested_variants = commodity_aliases.get(requested_commodity, {requested_commodity})
    return record_state == requested_state and (
        any(record_commodity == variant for variant in requested_variants)
        or any(record_commodity.startswith(f"{variant}(") for variant in requested_variants)
        or any(record_commodity.startswith(f"{variant} ") for variant in requested_variants)
    )

def _prediction(prices: list[int]) -> list[dict]:
    """Calculate the requested seven-day smoothed forecast."""
    if not prices:
        return []

    recent_prices = prices[-7:]
    average = sum(recent_prices) / len(recent_prices)
    trend = ((recent_prices[-1] - recent_prices[0]) / (len(recent_prices) - 1)
             if len(recent_prices) > 1 else 0)
    last_price = recent_prices[-1]
    predictions = []
    for day in range(1, 8):
        predicted_price = max(0, round(0.4 * (last_price + trend) + 0.6 * average))
        predictions.append({
            "day": day,
            "date": (date.today() + timedelta(days=day)).isoformat(),
            "predictedModalPrice": predicted_price,
        })
        last_price = predicted_price
    return predictions


def get_live_market_prices(commodity: str, state: str) -> dict:
    """Fetch live mandi prices and calculate a seven-day modal-price forecast."""
    if not config.DATA_GOV_API_KEY:
        raise RuntimeError("DATA_GOV_API_KEY is not configured")

    response = requests.get(
        f"https://api.data.gov.in/resource/{config.DATA_GOV_RESOURCE_ID}",
        params={
            "api-key": config.DATA_GOV_API_KEY,
            "format": "json",
            # The API's server-side filters intermittently hang. Fetch the
            # current bounded dataset and apply the two exact filters locally.
            "limit": 10000,
        },
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (AgriBot market service)",
        },
        timeout=(10, 35),
    )
    response.raise_for_status()
    payload = response.json()
    records = payload.get("records", []) if isinstance(payload, dict) else []
    if not isinstance(records, list):
        records = []

    live_prices = []
    numeric_prices = []
    records = [record for record in records if _matches_market(record, commodity, state)]

    for record in records:
        try:
            modal_price = float(_record_value(record, "Modal_Price", "modal_price", "Modal") or 0)
        except (TypeError, ValueError):
            modal_price = 0
        modal_price = int(modal_price) if modal_price else 0
        if modal_price:
            numeric_prices.append(modal_price)
        live_prices.append({
            "market": _record_value(record, "Market", "market_center", "market_name") or "-",
            "district": _record_value(record, "District", "district_name") or "-",
            "modalPrice": modal_price,
            "minPrice": _record_value(record, "Min_Price", "min_price") or "-",
            "maxPrice": _record_value(record, "Max_Price", "max_price") or "-",
            "date": _record_value(record, "Arrival_Date", "arrival_date", "date", "timestamp") or "-",
        })

    return {
        "crop": commodity.strip().title(),
        "state": state.strip().title(),
        "source": "agrimarket-live",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "currentPrice": numeric_prices[-1] if numeric_prices else None,
        "livePrices": live_prices,
        "predictions": _prediction(numeric_prices),
    }

