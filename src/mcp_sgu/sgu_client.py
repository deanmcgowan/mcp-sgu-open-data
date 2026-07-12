"""SGU OGC API Features client with pagination and retry support."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from mcp_sgu.cache import get_metadata_cache, get_results_cache
from mcp_sgu.config import get_settings
from mcp_sgu.logging_config import get_logger, log_upstream_call

logger = get_logger(__name__)

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0
_SGU_MAX_LIMIT = 1000  # SGU enforces this server-side


class SGUError(Exception):
    """Base class for SGU API errors."""


class SGUTimeoutError(SGUError):
    """SGU request timed out."""


class SGUUnavailableError(SGUError):
    """SGU API is unavailable."""


class SGUResponseError(SGUError):
    """SGU returned an unexpected response."""


class SGUClient:
    """Async client for the SGU OGC API Features endpoint."""

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.sgu_base_url).rstrip("/")
        self._semaphore = asyncio.Semaphore(settings.max_upstream_concurrency)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=_TIMEOUT,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "mcp-sgu-open-data/0.1.0 (+https://github.com/deanmcgowan/mcp-sgu-open-data)",
                },
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform a GET request with retry and backoff."""
        client = await self._get_client()
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            if attempt > 0:
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

            t0 = time.monotonic()
            try:
                async with self._semaphore:
                    resp = await client.get(url, params=params)
                duration_ms = (time.monotonic() - t0) * 1000
                log_upstream_call(logger, "sgu", url, resp.status_code, duration_ms)
                resp.raise_for_status()
                return resp.json()

            except httpx.TimeoutException as exc:
                duration_ms = (time.monotonic() - t0) * 1000
                log_upstream_call(logger, "sgu", url, 0, duration_ms, error="timeout")
                err = SGUTimeoutError(f"SGU request timed out: {url}")
                err.__cause__ = exc
                last_exc = err
                # Timeouts are retryable

            except httpx.HTTPStatusError as exc:
                duration_ms = (time.monotonic() - t0) * 1000
                status = exc.response.status_code
                log_upstream_call(logger, "sgu", url, status, duration_ms, error="http_error")
                # 5xx are retryable; 4xx are not
                if status < 500:
                    raise SGUResponseError(f"SGU returned HTTP {status} for {url}") from exc
                err = SGUUnavailableError(f"SGU returned HTTP {status} for {url}")
                err.__cause__ = exc
                last_exc = err

            except httpx.RequestError as exc:
                duration_ms = (time.monotonic() - t0) * 1000
                log_upstream_call(logger, "sgu", url, 0, duration_ms, error="request_error")
                err = SGUUnavailableError(f"SGU request failed: {exc}")
                err.__cause__ = exc
                last_exc = err

        raise last_exc or SGUUnavailableError(f"SGU request failed after {_MAX_RETRIES} attempts")

    # ── Metadata ──────────────────────────────────────────────────────────

    async def get_landing_page(self) -> dict[str, Any]:
        """Return the OGC API landing page."""
        cache = get_metadata_cache()
        settings = get_settings()
        key = f"landing:{self._base_url}"
        cached = await cache.get(key)
        if cached is not None:
            return cached
        data = await self._get(self._base_url)
        await cache.set(key, data, ttl=float(settings.cache_ttl_seconds))
        return data

    async def get_conformance(self) -> dict[str, Any]:
        """Return OGC API conformance classes."""
        cache = get_metadata_cache()
        settings = get_settings()
        key = f"conformance:{self._base_url}"
        cached = await cache.get(key)
        if cached is not None:
            return cached
        data = await self._get(f"{self._base_url}/conformance")
        await cache.set(key, data, ttl=float(settings.cache_ttl_seconds))
        return data

    async def get_collections(self) -> dict[str, Any]:
        """Return available collections."""
        cache = get_metadata_cache()
        settings = get_settings()
        key = f"collections:{self._base_url}"
        cached = await cache.get(key)
        if cached is not None:
            return cached
        data = await self._get(f"{self._base_url}/collections")
        await cache.set(key, data, ttl=float(settings.cache_ttl_seconds))
        return data

    async def get_collection(self, collection_id: str) -> dict[str, Any]:
        """Return metadata for a single collection."""
        cache = get_metadata_cache()
        settings = get_settings()
        key = f"collection:{self._base_url}:{collection_id}"
        cached = await cache.get(key)
        if cached is not None:
            return cached
        data = await self._get(f"{self._base_url}/collections/{collection_id}")
        await cache.set(key, data, ttl=float(settings.cache_ttl_seconds))
        return data

    async def get_queryables(self, collection_id: str) -> dict[str, Any]:
        """Return the queryable fields for a collection."""
        cache = get_metadata_cache()
        settings = get_settings()
        key = f"queryables:{self._base_url}:{collection_id}"
        cached = await cache.get(key)
        if cached is not None:
            return cached
        data = await self._get(f"{self._base_url}/collections/{collection_id}/queryables")
        await cache.set(key, data, ttl=float(settings.cache_ttl_seconds))
        return data

    # ── Features ──────────────────────────────────────────────────────────

    async def get_item(self, collection_id: str, feature_id: str) -> dict[str, Any]:
        """Return a single feature by its OGC feature ID."""
        data = await self._get(f"{self._base_url}/collections/{collection_id}/items/{feature_id}")
        return data

    async def get_items(
        self,
        collection_id: str,
        params: dict[str, Any] | None = None,
        *,
        max_records: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fetch items from a collection, following OGC next links.

        Returns a tuple of (features, last_response_metadata).
        ``last_response_metadata`` contains ``numberMatched``, ``numberReturned``, links etc.
        """
        effective_max = max_records if max_records is not None else get_settings().max_inline_results
        if effective_max < 1:
            raise ValueError("max_records must be positive")

        params = dict(params or {})
        next_url = params.pop("_next_url", None)
        # Enforce page size
        page_limit = min(params.get("limit", _SGU_MAX_LIMIT), _SGU_MAX_LIMIT, effective_max)
        params["limit"] = page_limit

        url = next_url or f"{self._base_url}/collections/{collection_id}/items"
        if next_url:
            params = None
        all_features: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        last_response: dict[str, Any] = {}
        seen_next_links: set[str] = set()

        while url:
            cache_key = f"items:{url}:{sorted(params.items()) if params else ''}"
            cache = get_results_cache()
            cached = await cache.get(cache_key)

            if cached is not None:
                data = cached
            else:
                data = await self._get(url, params)
                await cache.set(cache_key, data, ttl=60.0)

            last_response = data
            features = data.get("features", [])

            # Deduplicate by feature id
            for f in features:
                fid = f.get("id") or str(f.get("properties", {}).get("brunnsid", ""))
                if fid and fid in seen_ids:
                    logger.warning("Duplicate feature detected", extra={"feature_id": fid})
                    continue
                if fid:
                    seen_ids.add(fid)
                all_features.append(f)

            # Check limit
            if len(all_features) >= effective_max:
                all_features = all_features[:effective_max]
                last_response["_truncated"] = True
                break

            # Follow OGC next link
            next_url = _extract_next_link(data.get("links", []))
            if not next_url:
                break
            if next_url in seen_next_links:
                last_response["_truncated"] = True
                last_response["_truncation_reason"] = "repeated_next_link"
                break
            seen_next_links.add(next_url)
            url = next_url
            params = None  # next URL already encodes query params; must not pass {} as that strips them

        return all_features, last_response


def _extract_next_link(links: list[dict[str, Any]]) -> str | None:
    """Extract the ``next`` link from an OGC links array."""
    for link in links:
        if link.get("rel") == "next":
            return link.get("href")
    return None


# Module-level singleton
_client: SGUClient | None = None


def get_sgu_client() -> SGUClient:
    """Return the SGU client singleton."""
    global _client
    if _client is None:
        _client = SGUClient()
    return _client
