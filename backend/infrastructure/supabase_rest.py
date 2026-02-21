"""
Supabase REST Wrapper — No SDK dependency
Mimics supabase-py's .table().select().eq().execute() chaining
using httpx + PostgREST query params.

Used by: agent_service.py, premium_router.py
Pattern matches: infrastructure/supabase_client.py
"""

import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger("SupabaseREST")


class QueryResult:
    """Mimics supabase execute() result with .data attribute"""
    def __init__(self, data, count=None):
        self.data = data if data else []
        self.count = count


class TableQuery:
    """Chainable query builder for PostgREST API"""

    def __init__(self, base_url: str, key: str, table: str):
        self._base_url = f"{base_url}/rest/v1/{table}"
        self._key = key
        self._params = {}
        self._method = "GET"
        self._body = None
        self._extra_headers = {}
        self._want_single = False
        self._want_count = False

    def _headers(self):
        h = {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        h.update(self._extra_headers)
        return h

    # ── Query builders ──

    def select(self, columns: str = "*", count: str = None):
        self._method = "GET"
        self._params["select"] = columns
        if count == "exact":
            self._want_count = True
            self._extra_headers["Prefer"] = "count=exact"
        return self

    def insert(self, data):
        self._method = "POST"
        self._body = data
        return self

    def update(self, data: dict):
        self._method = "PATCH"
        self._body = data
        return self

    def upsert(self, data: dict, on_conflict: str = None):
        self._method = "POST"
        self._body = data
        self._extra_headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        if on_conflict:
            self._params["on_conflict"] = on_conflict
        return self

    def delete(self):
        self._method = "DELETE"
        return self

    # ── Filters ──

    def eq(self, column: str, value):
        self._params[column] = f"eq.{value}"
        return self

    def neq(self, column: str, value):
        self._params[column] = f"neq.{value}"
        return self

    # ── Modifiers ──

    def order(self, column: str, desc: bool = False):
        direction = "desc" if desc else "asc"
        self._params["order"] = f"{column}.{direction}"
        return self

    def limit(self, count: int):
        self._params["limit"] = str(count)
        return self

    def single(self):
        """Return single row (first match)"""
        self._want_single = True
        self._params["limit"] = "1"
        return self

    # ── Execute ──

    def execute(self) -> QueryResult:
        """Execute the query synchronously via httpx"""
        with httpx.Client(timeout=30.0) as client:
            try:
                headers = self._headers()
                if self._method == "GET":
                    resp = client.get(self._base_url, headers=headers, params=self._params)
                elif self._method == "POST":
                    resp = client.post(self._base_url, headers=headers, json=self._body, params=self._params)
                elif self._method == "PATCH":
                    resp = client.patch(self._base_url, headers=headers, json=self._body, params=self._params)
                elif self._method == "DELETE":
                    resp = client.delete(self._base_url, headers=headers, params=self._params)
                else:
                    return QueryResult([])

                if resp.status_code in [200, 201, 204]:
                    data = resp.json() if resp.text else []

                    # Parse count from content-range header
                    count_val = None
                    if self._want_count:
                        cr = resp.headers.get("content-range", "")
                        if "/" in cr:
                            try:
                                count_val = int(cr.split("/")[1])
                            except (ValueError, IndexError):
                                count_val = len(data) if isinstance(data, list) else 0

                    # Single mode: return first row as .data
                    if self._want_single and isinstance(data, list):
                        data = data[0] if data else None

                    return QueryResult(data, count=count_val)
                else:
                    logger.error(f"[SupabaseREST] {self._method} {self._base_url}: {resp.status_code} {resp.text[:300]}")
                    return QueryResult([])

            except Exception as e:
                logger.error(f"[SupabaseREST] Request failed: {e}")
                return QueryResult([])


class SupabaseREST:
    """Lightweight Supabase REST client mimicking SDK interface.
    No supabase-py dependency, no httpcore conflicts."""

    def __init__(self, url: str = None, key: str = None):
        self._url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self._key = key or os.getenv("SUPABASE_KEY", "")
        self._available = bool(self._url and self._key)

        if self._available:
            logger.info(f"[SupabaseREST] Configured for {self._url[:40]}...")
        else:
            logger.warning("[SupabaseREST] Missing SUPABASE_URL or SUPABASE_KEY")

    @property
    def is_available(self) -> bool:
        return self._available

    def table(self, name: str) -> TableQuery:
        return TableQuery(self._url, self._key, name)


# ── Singleton ──
_instance: Optional[SupabaseREST] = None

def get_supabase_rest() -> SupabaseREST:
    """Get singleton SupabaseREST client"""
    global _instance
    if _instance is None:
        _instance = SupabaseREST()
    return _instance
