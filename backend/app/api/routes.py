"""HTTP endpoints for the local Onshape AI Studio UI."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agent.planner import create_plan, validate_feature_payload
from app.ai.provider import AIProviderError
from app.onshape.client import OnshapeAPIError, OnshapeClient
from app.settings import Settings, get_settings
from app.usage.guard import RequestGuard

router = APIRouter(prefix="/api")
_guard = RequestGuard()


def get_guard() -> RequestGuard:
    return _guard


def get_onshape(settings: Settings = Depends(get_settings)) -> OnshapeClient:
    return OnshapeClient(settings, _guard)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    context: str = Field(default="", max_length=12000)


class CreateDocumentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class FeatureWriteRequest(BaseModel):
    feature: dict
    confirm: bool = False


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@router.get("/config")
async def config(settings: Settings = Depends(get_settings)):
    return {
        "app_name": settings.app_name,
        "ai_provider": settings.ai_provider,
        "onshape_configured": bool(settings.onshape_access_key and settings.onshape_secret_key.get_secret_value()),
        "cloud_ai_configured": bool(settings.cloud_ai_api_key.get_secret_value()),
        "ollama_model": settings.ollama_model,
        "cloud_ai_model": settings.cloud_ai_model,
    }


@router.get("/usage")
async def usage():
    return _guard.snapshot()


@router.get("/onshape/documents")
async def documents(client: OnshapeClient = Depends(get_onshape)):
    try:
        return await client.list_documents()
    except OnshapeAPIError as exc:
        raise _onshape_http_error(exc) from exc


@router.post("/onshape/documents")
async def create_document(body: CreateDocumentRequest, client: OnshapeClient = Depends(get_onshape)):
    try:
        return await client.create_document(body.name)
    except OnshapeAPIError as exc:
        raise _onshape_http_error(exc) from exc


@router.get("/onshape/documents/{did}/workspaces/{wid}/elements")
async def elements(did: str, wid: str, client: OnshapeClient = Depends(get_onshape)):
    try:
        return await client.list_elements(did, wid)
    except OnshapeAPIError as exc:
        raise _onshape_http_error(exc) from exc


@router.get("/onshape/documents/{did}/{wvm}/{wvmid}/elements/{eid}/features")
async def features(did: str, wvm: str, wvmid: str, eid: str, client: OnshapeClient = Depends(get_onshape)):
    try:
        return await client.get_part_studio_features(did, wvm, wvmid, eid)
    except OnshapeAPIError as exc:
        raise _onshape_http_error(exc) from exc


@router.post("/onshape/documents/{did}/workspaces/{wid}/elements/{eid}/features")
async def add_feature(did: str, wid: str, eid: str, body: FeatureWriteRequest, client: OnshapeClient = Depends(get_onshape)):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required before writing a CAD feature.")
    try:
        validate_feature_payload(body.feature)
        return await client.add_part_studio_feature(did, wid, eid, body.feature)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OnshapeAPIError as exc:
        raise _onshape_http_error(exc) from exc


@router.post("/ai/plan")
async def ai_plan(body: ChatRequest, settings: Settings = Depends(get_settings)):
    try:
        result = await create_plan(settings, body.prompt, body.context)
        return {"plan": result, "executed": False}
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _onshape_http_error(exc: OnshapeAPIError) -> HTTPException:
    headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
    return HTTPException(status_code=exc.status_code, detail=str(exc), headers=headers)
