"""
politician_data.py - Congressional STOCK Act disclosure scraper, committee matcher, and scorer.
Ingests US House and Senate stock trades, identifies member accumulation, evaluates
committee jurisdiction alignment (e.g. Energy & Commerce, Armed Services, Science & Tech),
and caches results locally to avoid unnecessary network overhead.
"""

import os
import re
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "congress_trades.json")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL = 43200  # 12 hours


# ---------------------------------------------------------------------
# High-Alpha Congressional Committees for Tech, Defense & Semiconductors
# ---------------------------------------------------------------------
HIGH_ALPHA_TECH_COMMITTEES: Dict[str, Dict[str, Any]] = {
    "Energy and Commerce": {
        "weight": 2.5,
        "jurisdiction": "Telecommunications, consumer tech, CHIPS Act supply chains, semiconductor manufacturing"
    },
    "Armed Services": {
        "weight": 2.2,
        "jurisdiction": "Defense computing, military microelectronics, DARPA AI initiatives, defense cloud contracts"
    },
    "Science, Space, and Technology": {
        "weight": 2.3,
        "jurisdiction": "Semiconductor R&D, NIST, NSF AI research, civil technology standards"
    },
    "Commerce, Science, and Transportation": {
        "weight": 2.5,
        "jurisdiction": "Senate tech oversight, AI policy, spectrum allocation, semiconductor grants"
    },
    "Foreign Affairs": {
        "weight": 2.0,
        "jurisdiction": "Semiconductor export controls to China, Taiwan defense, international tech sanctions"
    },
    "Intelligence": {
        "weight": 2.2,
        "jurisdiction": "Cybersecurity, national security AI, classified computing infrastructure"
    },
    "Appropriations": {
        "weight": 1.8,
        "jurisdiction": "Federal funding allocations for DoD, DoE, and CHIPS Act grants"
    },
    "Speaker Emerita": {
        "weight": 2.5,
        "jurisdiction": "Top leadership insider access, high-visibility market-moving tech allocations"
    }
}


# ---------------------------------------------------------------------
# Roster of Active Congressional Stock Traders & Official Committees
# ---------------------------------------------------------------------
CONGRESS_MEMBERS_COMMITTEES: Dict[str, Dict[str, Any]] = {
    "Rick Allen": {
        "chamber": "House", "state": "GA", "party": "R",
        "committees": [
            "Energy and Commerce",
            "Education and the Workforce"
        ]
    },
    "Pete Sessions": {
        "chamber": "House", "state": "TX", "party": "R",
        "committees": ["Financial Services", "Oversight and Accountability"]
    },
    "Scott Franklin": {
        "chamber": "House", "state": "FL", "party": "R",
        "committees": ["Appropriations", "Science, Space, and Technology", "Veterans' Affairs"]
    },
    "Nancy Pelosi": {
        "chamber": "House", "state": "CA", "party": "D",
        "committees": ["Speaker Emerita"]
    },
    "Michael McCaul": {
        "chamber": "House", "state": "TX", "party": "R",
        "committees": ["Foreign Affairs", "Homeland Security"]
    },
    "Ro Khanna": {
        "chamber": "House", "state": "CA", "party": "D",
        "committees": ["Armed Services", "Oversight and Accountability"]
    },
    "Tommy Tuberville": {
        "chamber": "Senate", "state": "AL", "party": "R",
        "committees": ["Armed Services", "Agriculture", "Veterans' Affairs"]
    },
    "Markwayne Mullin": {
        "chamber": "Senate", "state": "OK", "party": "R",
        "committees": ["Armed Services", "Environment and Public Works", "Health, Education, Labor and Pensions"]
    },
    "Dan Sullivan": {
        "chamber": "Senate", "state": "AK", "party": "R",
        "committees": ["Armed Services", "Commerce, Science, and Transportation", "Veterans' Affairs"]
    },
    "Sheldon Whitehouse": {
        "chamber": "Senate", "state": "RI", "party": "D",
        "committees": ["Budget", "Finance", "Environment and Public Works", "Judiciary"]
    },
    "Josh Gottheimer": {
        "chamber": "House", "state": "NJ", "party": "D",
        "committees": ["Financial Services", "Intelligence"]
    },
    "Kevin Hern": {
        "chamber": "House", "state": "OK", "party": "R",
        "committees": ["Ways and Means"]
    },
    "Marjorie Taylor Greene": {
        "chamber": "House", "state": "GA", "party": "R",
        "committees": ["Homeland Security", "Oversight and Accountability"]
    },
    "Scott Peters": {
        "chamber": "House", "state": "CA", "party": "D",
        "committees": ["Energy and Commerce", "Budget"]
    },
    "John Curtis": {
        "chamber": "House", "state": "UT", "party": "R",
        "committees": ["Energy and Commerce"]
    },
    "Lois Frankel": {
        "chamber": "House", "state": "FL", "party": "D",
        "committees": ["Appropriations", "Veterans' Affairs"]
    },
    "Debbie Wasserman Schultz": {
        "chamber": "House", "state": "FL", "party": "D",
        "committees": ["Appropriations", "Select Subcommittee on the Weaponization of the Federal Government"]
    },
    "Sheri Biggs": {
        "chamber": "House", "state": "SC", "party": "R",
        "committees": []
    }
}


def normalize_politician_name(raw_name: str) -> str:
    """
    Cleans raw scraper strings like 'Rick AllenRepublicanHouseGA' into 'Rick Allen'.
    """
    if not raw_name:
        return ""
    # Strip party/chamber/state suffix e.g. RepublicanHouseGA, DemocratSenateCA
    cleaned = re.sub(r'(Republican|Democrat|Independent)(House|Senate)[A-Z]{2}$', '', raw_name).strip()
    return cleaned if cleaned else raw_name.strip()


def get_politician_committee_info(politician_raw: str) -> Dict[str, Any]:
    """
    Matches a politician to known committees and determines if they sit on
    high-alpha tech/defense/semiconductor oversight committees.
    """
    norm_name = normalize_politician_name(politician_raw)
    
    # Try exact match or fuzzy prefix match
    member_data = None
    matched_key = None
    for key, data in CONGRESS_MEMBERS_COMMITTEES.items():
        if key.lower() == norm_name.lower() or norm_name.lower().startswith(key.lower()):
            member_data = data
            matched_key = key
            break
            
    if not member_data:
        return {
            "normalized_name": norm_name,
            "chamber": "",
            "state": "",
            "party": "",
            "committees": [],
            "matched_alpha_committees": [],
            "jurisdiction_match": False,
            "jurisdiction_weight": 1.0,
            "jurisdiction_notes": ""
        }
        
    committees = member_data.get("committees", [])
    matched_alpha = []
    max_weight = 1.0
    notes = []
    
    for comm in committees:
        for alpha_name, alpha_info in HIGH_ALPHA_TECH_COMMITTEES.items():
            if alpha_name.lower() in comm.lower():
                matched_alpha.append(alpha_name)
                if alpha_info["weight"] > max_weight:
                    max_weight = alpha_info["weight"]
                notes.append(f"{alpha_name} ({alpha_info['jurisdiction']})")
                
    has_match = len(matched_alpha) > 0
    return {
        "normalized_name": matched_key,
        "chamber": member_data.get("chamber", ""),
        "state": member_data.get("state", ""),
        "party": member_data.get("party", ""),
        "committees": committees,
        "matched_alpha_committees": list(set(matched_alpha)),
        "jurisdiction_match": has_match,
        "jurisdiction_weight": max_weight if has_match else 1.0,
        "jurisdiction_notes": " | ".join(notes)
    }


def parse_trade_row(row_cells: List[str]) -> Optional[Dict[str, Any]]:
    """
    Parses a single row from CapitolTrades.
    Format typically: [Politician, Traded Issuer, Published, Traded, Filed After, Owner, Type, Size, Price, ...]
    """
    if len(row_cells) < 8:
        return None

    politician_raw = row_cells[0].strip()
    issuer_raw = row_cells[1].strip()
    published_date_str = row_cells[2].strip()
    traded_date_str = row_cells[3].strip()
    trade_type = row_cells[6].strip().lower()  # 'buy' or 'sell'
    trade_size = row_cells[7].strip()

    # Extract ticker from issuer string like 'Apple IncAAPL:US' or 'NVIDIA CorpNVDA:US'
    ticker_match = re.search(r'([A-Z]{1,5}):US', issuer_raw)
    ticker = ticker_match.group(1) if ticker_match else None
    if not ticker:
        tail_match = re.search(r'([A-Z]{1,5})$', issuer_raw)
        ticker = tail_match.group(1) if tail_match else None

    if not ticker:
        return None

    clean_date_str = re.sub(r'(\d{1,2})\s*([A-Za-z]+)\s*(\d{4})', r'\1 \2 \3', traded_date_str)
    try:
        for full_m, abbr in [("Sept", "Sep")]:
            clean_date_str = clean_date_str.replace(full_m, abbr)
        traded_dt = datetime.strptime(clean_date_str, "%d %b %Y").replace(tzinfo=timezone.utc)
        traded_date_iso = traded_dt.strftime("%Y-%m-%d")
    except Exception:
        traded_date_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    comm_info = get_politician_committee_info(politician_raw)

    return {
        "politician": politician_raw,
        "politician_name": comm_info["normalized_name"],
        "ticker": ticker.upper(),
        "issuer": issuer_raw,
        "type": "BUY" if "buy" in trade_type else "SELL",
        "size": trade_size,
        "traded_date": traded_date_iso,
        "published_date": published_date_str,
        "chamber": comm_info["chamber"],
        "state": comm_info["state"],
        "party": comm_info["party"],
        "committees": comm_info["committees"],
        "jurisdiction_match": comm_info["jurisdiction_match"],
        "jurisdiction_weight": comm_info["jurisdiction_weight"],
        "jurisdiction_notes": comm_info["jurisdiction_notes"]
    }


def fetch_congress_trades(max_pages: int = 5, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetches recent Congressional trades from CapitolTrades with disk caching.
    """
    now = time.time()
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            mtime = os.path.getmtime(CACHE_FILE)
            if now - mtime < CACHE_TTL:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    if cached_data:
                        # Re-enrich cached data with committee jurisdiction info
                        for t in cached_data:
                            if "jurisdiction_match" not in t:
                                c_info = get_politician_committee_info(t.get("politician", ""))
                                t["politician_name"] = c_info["normalized_name"]
                                t["committees"] = c_info["committees"]
                                t["jurisdiction_match"] = c_info["jurisdiction_match"]
                                t["jurisdiction_weight"] = c_info["jurisdiction_weight"]
                                t["jurisdiction_notes"] = c_info["jurisdiction_notes"]
                        return cached_data
        except Exception:
            pass

    trades: List[Dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        for page in range(1, max_pages + 1):
            url = f"https://www.capitoltrades.com/trades?page={page}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")
            if not table:
                break
            trs = table.find_all("tr")
            for tr in trs[1:]:  # skip header
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                parsed = parse_trade_row(cells)
                if parsed:
                    trades.append(parsed)
            time.sleep(0.3)
    except Exception as e:
        print(f"Warning: Failed to fetch online congress data: {e}")

    if trades:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(trades, f, indent=2)
            return trades
        except Exception:
            return trades

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                for t in cached:
                    if "jurisdiction_match" not in t:
                        c_info = get_politician_committee_info(t.get("politician", ""))
                        t["politician_name"] = c_info["normalized_name"]
                        t["committees"] = c_info["committees"]
                        t["jurisdiction_match"] = c_info["jurisdiction_match"]
                        t["jurisdiction_weight"] = c_info["jurisdiction_weight"]
                        t["jurisdiction_notes"] = c_info["jurisdiction_notes"]
                return cached
        except Exception:
            pass

    return []


def get_ticker_congress_signals(
    ticker: str,
    days: int = 45,
    all_trades: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Computes Congressional Smart-Money signals for a specific ticker over a recent window,
    evaluating committee jurisdiction relevance, trade size conviction, and buy/sell balance.
    """
    ticker = ticker.upper().strip()
    trades = all_trades if all_trades is not None else fetch_congress_trades()
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    ticker_trades = [
        t for t in trades
        if t.get("ticker") == ticker and t.get("traded_date", "") >= cutoff_date
    ]

    # Ensure committee enrichment
    enriched_trades = []
    for t in ticker_trades:
        trade_copy = dict(t)
        if "jurisdiction_match" not in trade_copy:
            c_info = get_politician_committee_info(trade_copy.get("politician", ""))
            trade_copy["politician_name"] = c_info["normalized_name"]
            trade_copy["committees"] = c_info["committees"]
            trade_copy["jurisdiction_match"] = c_info["jurisdiction_match"]
            trade_copy["jurisdiction_weight"] = c_info["jurisdiction_weight"]
            trade_copy["jurisdiction_notes"] = c_info["jurisdiction_notes"]
        enriched_trades.append(trade_copy)

    buy_trades = [t for t in enriched_trades if t.get("type") == "BUY"]
    sell_trades = [t for t in enriched_trades if t.get("type") == "SELL"]

    politicians = list({t.get("politician_name") or t["politician"] for t in enriched_trades if "politician" in t})
    has_recent_buy = len(buy_trades) > 0

    # Committee jurisdiction matching
    jurisdiction_buys = [t for t in buy_trades if t.get("jurisdiction_match")]
    has_jurisdiction_match = len(jurisdiction_buys) > 0
    matched_committees = list({
        comm
        for t in jurisdiction_buys
        for comm in t.get("committees", [])
        if any(alpha in comm for alpha in HIGH_ALPHA_TECH_COMMITTEES)
    })
    high_jurisdiction_buyers = list({
        t.get("politician_name") or t["politician"]
        for t in jurisdiction_buys
    })

    # Conviction scoring (0 to 100)
    congress_score = 0
    if has_recent_buy:
        congress_score = 30  # Base buy score
        
        # Committee multiplier
        max_multiplier = max([t.get("jurisdiction_weight", 1.0) for t in buy_trades], default=1.0)
        congress_score = int(congress_score * max_multiplier)
        
        # Trade size conviction bonus
        for b in buy_trades:
            size_str = str(b.get("size", "")).upper()
            if "500K" in size_str or "1M" in size_str or "5M" in size_str:
                congress_score += 25
                break
            elif "100K" in size_str or "250K" in size_str:
                congress_score += 15
                break
            elif "50K" in size_str:
                congress_score += 10
                break
                
        # Cluster politician buying bonus (2+ distinct members)
        if len(set(high_jurisdiction_buyers)) >= 2:
            congress_score += 20
            
        congress_score = min(100, congress_score)
        
    elif len(sell_trades) > 0:
        # Negative signal if high jurisdiction member is selling
        has_jurisdiction_sell = any(t.get("jurisdiction_match") for t in sell_trades)
        congress_score = -20 if has_jurisdiction_sell else -10

    return {
        "ticker": ticker,
        "window_days": days,
        "total_trades": len(enriched_trades),
        "buy_count": len(buy_trades),
        "sell_count": len(sell_trades),
        "has_recent_buy": has_recent_buy,
        "has_jurisdiction_match": has_jurisdiction_match,
        "matched_committees": matched_committees,
        "high_jurisdiction_buyers": high_jurisdiction_buyers,
        "congress_score": congress_score,
        "politicians": politicians[:5],
        "trades": enriched_trades
    }
