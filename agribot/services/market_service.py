"""
Market Price Service
Returns crop mandi prices. Uses a static dataset now;
swap _fetch_live() to connect a real API (e.g. data.gov.in Agmarknet).
"""
import random
from datetime import date, timedelta

# Base prices in INR per quintal (100 kg)
BASE_PRICES = {
    "Tomato":   1800, "Onion":    1200, "Potato":   900,
    "Wheat":    2200, "Rice":     2100, "Maize":    1600,
    "Cotton":   6000, "Soybean":  4200, "Groundnut":5500,
    "Sugarcane": 350, "Mango":    3500, "Banana":   1400,
    "Chilli":   9000, "Turmeric": 7500, "Ginger":   4000,
    "Garlic":   8000, "Peas":     3000, "Mustard":  5200,
    "Sunflower":5100, "Sesame":   9500,
}


def _price_with_noise(base: int, seed: int) -> int:
    random.seed(seed)
    return int(base * (1 + random.uniform(-0.05, 0.05)))


def get_market_prices() -> list:
    today = date.today().toordinal()
    prices = []
    for crop, base in BASE_PRICES.items():
        today_price     = _price_with_noise(base, today + hash(crop))
        yesterday_price = _price_with_noise(base, today - 1 + hash(crop))
        week_ago_price  = _price_with_noise(base, today - 7 + hash(crop))
        trend = "up" if today_price > yesterday_price else ("down" if today_price < yesterday_price else "stable")
        prices.append({
            "crop":            crop,
            "today_price":     today_price,
            "yesterday_price": yesterday_price,
            "week_ago_price":  week_ago_price,
            "unit":            "₹/quintal",
            "trend":           trend,
            "change":          today_price - yesterday_price,
            "change_pct":      round((today_price - yesterday_price) / yesterday_price * 100, 1),
        })
    return sorted(prices, key=lambda x: x["crop"])


def get_price_for_crop(crop_name: str) -> dict | None:
    crop_name_title = crop_name.strip().title()
    for item in get_market_prices():
        if item["crop"].lower() == crop_name_title.lower():
            return item
    return None


def prices_to_text() -> str:
    lines = ["Crop Market Prices (INR/quintal):"]
    for item in get_market_prices():
        arrow = "↑" if item["trend"] == "up" else ("↓" if item["trend"] == "down" else "→")
        lines.append(
            f"  {item['crop']}: ₹{item['today_price']} {arrow} "
            f"({item['change_pct']:+.1f}% vs yesterday)"
        )
    return "\n".join(lines)
