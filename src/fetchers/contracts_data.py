"""
contracts_data.py - US Federal Government Contract Awards Ingestion & Scorer (USASpending.gov).
Ingests official Department of Defense (DoD), Department of Energy (DoE), NASA, and intelligence
contract awards directly from the official US government API (api.usaspending.gov) with zero API keys.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL = 86400  # 24 hours (federal contract data updates daily)

API_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# Corporate legal entities mapping for the Wave Rider 50 universe
TICKER_CONTRACT_KEYWORDS: Dict[str, List[str]] = {
    "DELL": ["DELL MARKETING L.P.", "DELL FEDERAL SYSTEMS"],
    "INTC": ["INTEL FEDERAL LLC", "INTEL CORPORATION"],
    "NVDA": ["NVIDIA CORPORATION"],
    "MSFT": ["MICROSOFT CORPORATION"],
    "AMZN": ["AMAZON WEB SERVICES", "AMAZON.COM"],
    "GOOGL": ["GOOGLE LLC", "ALPHABET INC"],
    "AAPL": ["APPLE INC"],
    "AVGO": ["BROADCOM INC"],
    "QCOM": ["QUALCOMM TECHNOLOGIES", "QUALCOMM INC"],
    "TXN": ["TEXAS INSTRUMENTS INC"],
    "AMAT": ["APPLIED MATERIALS INC"],
    "LRCX": ["LAM RESEARCH CORP"],
    "KLAC": ["KLA CORPORATION"],
    "MU": ["MICRON TECHNOLOGY INC"],
    "WDC": ["WESTERN DIGITAL TECHNOLOGIES"],
    "STX": ["SEAGATE US LLC", "SEAGATE TECHNOLOGY"],
    "SMCI": ["SUPER MICRO COMPUTER INC"],
    "AMD": ["ADVANCED MICRO DEVICES INC"],
    "TSM": ["TAIWAN SEMICONDUCTOR"],
    "ASML": ["ASML US LLC", "ASML HOLDING"],
    "PLTR": ["PALANTIR USG", "PALANTIR TECHNOLOGIES"],
    "ORCL": ["ORACLE AMERICA INC", "ORACLE CORPORATION"],
    "PANW": ["PALO ALTO NETWORKS"],
    "CRWD": ["CROWDSTRIKE INC"],
    "ETN": ["EATON CORPORATION", "EATON AEROQUIP"],
    "ANET": ["ARISTA NETWORKS INC"],
    "VRT": ["VERTIV CORPORATION", "LIEBERT CORPORATION"],
    "NOW": ["SERVICENOW INC"],
    "CRM": ["SALESFORCE.COM INC", "SALESFORCE INC"]
}


def fetch_federal_contracts(ticker: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetches official US federal government contract awards for a ticker via api.usaspending.gov.
    Utilizes local disk caching with 24-hour TTL to prevent network overhead.
    """
    ticker = ticker.upper().strip()
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_contracts.json")
    now = time.time()

    if not force_refresh and os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if now - mtime < CACHE_TTL:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

    keywords = TICKER_CONTRACT_KEYWORDS.get(ticker, [ticker])
    headers = {"Content-Type": "application/json"}
    
    # Query past 2 years of active federal commitments
    payload = {
        "filters": {
            "time_period": [
                {
                    "start_date": "2024-01-01",
                    "end_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                }
            ],
            "award_type_codes": ["A", "B", "C", "D"],  # Prime Contracts
            "keywords": keywords
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Description",
            "Awarding Agency",
            "Awarding Sub Agency",
            "Action Date"
        ],
        "limit": 15,
        "sort": "Award Amount",
        "order": "desc"
    }

    contracts: List[Dict[str, Any]] = []
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=8)
        if r.status_code == 200:
            raw_results = r.json().get("results", [])
            for item in raw_results:
                amt = float(item.get("Award Amount") or 0.0)
                contracts.append({
                    "award_id": item.get("Award ID"),
                    "recipient": item.get("Recipient Name"),
                    "amount_usd": round(amt, 2),
                    "agency": item.get("Awarding Agency"),
                    "sub_agency": item.get("Awarding Sub Agency"),
                    "description": item.get("Description") or "Federal Technology Procurement",
                    "action_date": item.get("Action Date") or "Active"
                })
    except Exception as e:
        print(f"Warning: Failed to fetch federal contracts for {ticker}: {e}")

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(contracts, f, indent=2)
    except Exception:
        pass

    return contracts


def get_ticker_contract_signals(ticker: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Evaluates federal government contract strength, total dollar value, defense presence,
    and assigns a quantitative contract score (0-100).
    """
    ticker = ticker.upper().strip()
    contracts = fetch_federal_contracts(ticker, force_refresh=force_refresh)

    total_value = sum(c.get("amount_usd", 0.0) for c in contracts)
    contract_count = len(contracts)
    top_award = max((c.get("amount_usd", 0.0) for c in contracts), default=0.0)

    agencies = list({c.get("agency") for c in contracts if c.get("agency")})
    
    # Check for Defense / Military presence
    defense_keywords = ["defense", "darpa", "iarpa", "army", "navy", "air force", "cyber command"]
    is_defense = any(
        any(dk in str(c.get("agency", "")).lower() or dk in str(c.get("sub_agency", "")).lower() or dk in str(c.get("description", "")).lower() for dk in defense_keywords)
        for c in contracts
    )

    has_major_contract = top_award >= 25_000_000.0 or total_value >= 50_000_000.0

    # Calculate Contract Score (0 to 100)
    score = 0
    if total_value >= 500_000_000.0:  # $500M+ mega contractor (DELL, MSFT)
        score = 95
    elif total_value >= 100_000_000.0:
        score = 80
    elif total_value >= 25_000_000.0:
        score = 65
    elif total_value >= 5_000_000.0:
        score = 45
    elif total_value > 0:
        score = 25

    if is_defense and score > 0:
        score = min(100, score + 10)  # Defense contracts have guaranteed strategic backing

    return {
        "ticker": ticker,
        "contract_count": contract_count,
        "total_contract_value_usd": round(total_value, 2),
        "top_award_amount_usd": round(top_award, 2),
        "has_major_contract": has_major_contract,
        "is_defense_contract": is_defense,
        "contract_score": score,
        "top_agencies": agencies[:6],
        "recent_contracts": contracts[:8]
    }
