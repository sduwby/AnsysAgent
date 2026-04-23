"""
database_tools.py — Motor design result database (pure JSON, no PyAEDT dependency).

Storage: ~/.AnsysAgent/designs/db.json
Schema per record:
{
    "id": str,          # UUID4
    "name": str,        # human-readable label
    "timestamp": str,   # ISO-8601
    "tags": [str],      # optional search tags
    "params": {...},    # design parameters dict
    "results": {...},   # KPI / simulation results dict
    "notes": str        # free-text notes
}
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.paths import ANSYS_DATA_DIR
from tools.utils import _ok, _err

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DB_PATH: Path = Path(ANSYS_DATA_DIR) / "designs" / "db.json"


def _load_db() -> list[dict]:
    """Return the full DB list; creates the file if absent."""
    if not _DB_PATH.exists():
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DB_PATH.write_text("[]", encoding="utf-8")
        return []
    try:
        return json.loads(_DB_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_db(records: list[dict]) -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DB_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_design_result(
    name: str,
    params: dict[str, Any],
    results: dict[str, Any],
    tags: list[str] | None = None,
    notes: str = "",
) -> dict:
    """Save a design + KPI record to the database.

    Args:
        name:    Human-readable label for this design entry.
        params:  Dict of design parameters (e.g. {"slot_depth_mm": 12.5, ...}).
        results: Dict of simulation KPIs (e.g. {"torque_Nm": 4.2, ...}).
        tags:    Optional list of string tags for later filtering.
        notes:   Free-text notes.

    Returns:
        Success result with the generated record ``id``.
    """
    if not name or not isinstance(name, str):
        return _err("'name' must be a non-empty string.")
    if not isinstance(params, dict):
        return _err("'params' must be a dict.")
    if not isinstance(results, dict):
        return _err("'results' must be a dict.")

    record: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "name": name,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "tags": tags if isinstance(tags, list) else [],
        "params": params,
        "results": results,
        "notes": notes,
    }

    try:
        db = _load_db()
        db.append(record)
        _save_db(db)
    except Exception as exc:
        return _err(f"Failed to save design result: {exc}")

    return _ok({"id": record["id"], "message": f"Design '{name}' saved successfully."})


def list_design_results(
    tag: str | None = None,
    name_contains: str | None = None,
    limit: int = 50,
) -> dict:
    """List design records, optionally filtered by tag or name substring.

    Args:
        tag:           If provided, only return records that contain this tag.
        name_contains: If provided, only return records whose name contains this
                       string (case-insensitive).
        limit:         Maximum number of records to return (newest-first). Default 50.

    Returns:
        Success result with a list of record summaries (id, name, timestamp, tags).
    """
    try:
        db = _load_db()
    except Exception as exc:
        return _err(f"Failed to load database: {exc}")

    filtered = db
    if tag:
        filtered = [r for r in filtered if tag in r.get("tags", [])]
    if name_contains:
        lc = name_contains.lower()
        filtered = [r for r in filtered if lc in r.get("name", "").lower()]

    # Newest-first
    filtered = sorted(filtered, key=lambda r: r.get("timestamp", ""), reverse=True)
    limited = filtered[:limit]

    summaries = [
        {
            "id": r["id"],
            "name": r["name"],
            "timestamp": r["timestamp"],
            "tags": r.get("tags", []),
        }
        for r in limited
    ]

    return _ok({"count": len(summaries), "records": summaries})


def get_design_result(record_id: str) -> dict:
    """Retrieve a single design record by its UUID.

    Args:
        record_id: The UUID string returned when the record was saved.

    Returns:
        Success result with the full record (params, results, notes, …).
    """
    if not record_id:
        return _err("'record_id' must be provided.")

    try:
        db = _load_db()
    except Exception as exc:
        return _err(f"Failed to load database: {exc}")

    for record in db:
        if record.get("id") == record_id:
            return _ok({"record": record})

    return _err(f"No record found with id '{record_id}'.")


def compare_design_results(record_ids: list[str], metrics: list[str] | None = None) -> dict:
    """Compare multiple design records side-by-side on selected result metrics.

    Args:
        record_ids: List of 2–10 UUID strings to compare.
        metrics:    Optional list of result keys to include in the comparison.
                    If omitted, all keys present in any of the selected records
                    are included.

    Returns:
        Success result with a comparison table:
        ``{"metrics": [...], "rows": [{"id": ..., "name": ..., <metric>: ..., ...}]}``.
    """
    if not isinstance(record_ids, list) or len(record_ids) < 2:
        return _err("'record_ids' must be a list with at least 2 entries.")
    if len(record_ids) > 10:
        return _err("Cannot compare more than 10 records at once.")

    try:
        db = _load_db()
    except Exception as exc:
        return _err(f"Failed to load database: {exc}")

    id_set = set(record_ids)
    selected = [r for r in db if r.get("id") in id_set]

    if len(selected) < len(record_ids):
        found_ids = {r["id"] for r in selected}
        missing = id_set - found_ids
        return _err(f"Records not found: {', '.join(missing)}")

    # Determine metrics to compare
    if metrics:
        compare_keys = metrics
    else:
        compare_keys_set: set[str] = set()
        for r in selected:
            compare_keys_set.update(r.get("results", {}).keys())
        compare_keys = sorted(compare_keys_set)

    rows = []
    for r in selected:
        row: dict[str, Any] = {"id": r["id"], "name": r["name"], "timestamp": r["timestamp"]}
        for key in compare_keys:
            row[key] = r.get("results", {}).get(key, None)
        rows.append(row)

    return _ok({"metrics": compare_keys, "rows": rows})
