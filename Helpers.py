import Constants
import pandas as pd


def extract_segment(
    text: str, keyword: str, window_before: int = 120, window_after: int = 900
):
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return None
    start = max(0, idx - window_before)
    end = min(len(text), idx + len(keyword) + window_after)
    return text[start:end]


def extract_all_currency_price_pairs(text: str):
    pairs = []

    for regex in (Constants.PRICE_REGEX_BEFORE, Constants.PRICE_REGEX_AFTER):
        for match in regex.finditer(text):
            raw_currency = match.group("currency").strip()
            raw_amount = match.group("amount").strip()

            currency = raw_currency.strip()
            amount = raw_amount.strip()

            if amount is not None:
                pairs.append((currency, amount))

    unique_pairs = []
    seen = set()
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            unique_pairs.append(pair)

    return unique_pairs


def extract_price(text: str):
    pairs = extract_all_currency_price_pairs(text)

    if not pairs:
        return None, None

    currency, amount = pairs[0]  # just take first match
    return currency, amount


def make_row(
    platform,
    region,
    currency,
    price,
    plan_type,
    scraped_at,
):
    return {
        "platform": platform,
        "region": region["name"],
        "currency": currency,
        "price": price,
        "plan_type": plan_type,
        "scraped_at": scraped_at,
    }
