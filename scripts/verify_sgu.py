"""Manually verify the live SGU Brunnar schema before production deployment."""

from __future__ import annotations

import asyncio
import json

import httpx

BASE_URL = "https://api.sgu.se/oppnadata/brunnar/ogc/features/v1"


async def main() -> None:
    """Print current queryables, collection metadata, and a paginated sample."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for path in (
            "/collections/brunnar",
            "/collections/brunnar/queryables",
            "/collections/brunnar-lager/queryables",
            "/collections/brunnar/items?limit=1",
        ):
            response = await client.get(f"{BASE_URL}{path}")
            response.raise_for_status()
            print(f"\n{path}\n{json.dumps(response.json(), ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
