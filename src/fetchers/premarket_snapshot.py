"""
premarket_snapshot.py - Static Pre-Market Snapshot Manager.
Freezes and persists the finalized pre-market ranking for all 50 watchlist equities
at 09:30 EST (15:30 CET). Prevents regular-hours intraday price drift from corrupting
historical pre-market gap metrics.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.fetchers.market_hours import get_ny_now

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cache", "premarket_snapshots")


def get_snapshot_path(date_str: Optional[str] = None) -> str:
    """Returns absolute path to the snapshot file for a given YYYY-MM-DD date."""
    if date_str is None:
        date_str = get_ny_now().strftime("%Y-%m-%d")
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    return os.path.join(SNAPSHOT_DIR, f"snapshot_{date_str}.json")


def has_premarket_snapshot(date_str: Optional[str] = None) -> bool:
    """Checks if a pre-market snapshot has already been frozen for the given date."""
    return os.path.exists(get_snapshot_path(date_str))


def save_premarket_snapshot(records: List[Dict[str, Any]], date_str: Optional[str] = None) -> str:
    """Persists a list of pre-market stock records into an immutable JSON snapshot."""
    path = get_snapshot_path(date_str)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "date": date_str or get_ny_now().strftime("%Y-%m-%d"),
        "created_at": datetime.now().isoformat(),
        "total_equities": len(records),
        "equities": records
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def load_premarket_snapshot(date_str: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """Loads frozen pre-market records from disk if present."""
    path = get_snapshot_path(date_str)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("equities", [])
    except Exception:
        return None
