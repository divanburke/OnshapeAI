"""Conservative async Onshape REST client with signed requests and GET caching."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import httpx

from app.security.onshape_signing import build_onshape_headers
from app.settings import Settings
from app.usage.guard import RequestGuard


class OnshapeAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class OnshapeClient:
    def __init__(self, settings: Settings, guard: RequestGuard):
        self.settings = settings
        self.guard = guard
        self.base_url = settings.onshape_base_url.rstrip("/")
        self.api_version = "v10"
        self.timeout = settings.onshape_request_timeout_seconds

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{self.api_version}/{path.lstrip('/')}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        cache: bool = False,
    ) -> Any:
        method = method.upper()
        url = self._url(path)
        cache_key = f"{method}:{url}:{params or {}}"
        if method == "GET" and cache:
            cached = self.guard.cache_get(cache_key)
            if cached is not None:
                return cached

        access_key = self.settings.onshape_access_key
        secret_key = self.settings.onshape_secret_key.get_secret_value()
        async with self.guard.semaphore:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                # A single bounded retry for transient server errors. 429 is
                # surfaced with Retry-After so the UI can explain the wait.
                for attempt in range(2):
                    request = client.build_request(method, url, params=params, json=json_body)
                    headers = build_onshape_headers(
                        method, str(request.url), access_key, secret_key
                    )
                    request.headers.update(headers)
                    response = await client.send(request)
                    self.guard.record(response.status_code)
                    if response.status_code == 429:
                        raise OnshapeAPIError(
                            429,
                            "Onshape rate limit reached for this endpoint.",
                            response.headers.get("Retry-After"),
                        )
                    if response.status_code == 402:
                        raise OnshapeAPIError(
                            402,
                            "Onshape reports that the annual API-call allocation has been reached. Check account usage in Onshape.",
                        )
                    if response.status_code in (500, 502, 503, 504) and attempt == 0:
                        await asyncio.sleep(1.0)
                        continue
                    if response.is_redirect:
                        raise OnshapeAPIError(
                            response.status_code,
                            "Onshape returned a redirect. This endpoint needs a redirect-specific signed request before it can be followed safely.",
                        )
                    if response.is_error:
                        detail = response.text[:1200]
                        raise OnshapeAPIError(response.status_code, detail or "Onshape request failed.")
                    if response.status_code == 204 or not response.content:
                        return None
                    try:
                        data = response.json()
                    except ValueError as exc:
                        raise OnshapeAPIError(response.status_code, "Onshape returned a non-JSON response.") from exc
                    if method == "GET" and cache:
                        self.guard.cache_set(cache_key, data)
                    return data
        raise OnshapeAPIError(503, "Onshape did not respond after a bounded retry.")

    async def list_documents(self) -> Any:
        return await self.request("GET", "documents", params={"limit": 50}, cache=True)

    async def create_document(self, name: str) -> Any:
        return await self.request("POST", "documents", json_body={"name": name})

    async def list_elements(self, did: str, wid: str) -> Any:
        return await self.request(
            "GET", f"documents/d/{did}/w/{wid}/elements", cache=True
        )

    async def get_part_studio_features(self, did: str, wvm: str, wvmid: str, eid: str) -> Any:
        return await self.request(
            "GET", f"partstudios/d/{did}/{wvm}/{wvmid}/e/{eid}/features",
            params={"rollbackBarIndex": -1, "includeGeometryIds": "true", "noSketchGeometry": "true"},
            cache=True,
        )

    async def add_part_studio_feature(
        self, did: str, wid: str, eid: str, feature: dict[str, Any]
    ) -> Any:
        return await self.request(
            "POST", f"partstudios/d/{did}/w/{wid}/e/{eid}/features", json_body=feature
        )
