from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.dependencies import get_app_settings, get_current_admin
from app.schemas import AiQueryRequest, AiQueryResponse

router = APIRouter(prefix="/ai", tags=["admin-ai"])


@router.post("/query", response_model=AiQueryResponse)
async def ai_query(
    payload: AiQueryRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _admin=Depends(get_current_admin),
):
    from app.services.ai_service import query_ai

    result = await query_ai(
        question=payload.question,
        session=db,
        settings=settings,
        context_hint=payload.context_hint,
    )
    return AiQueryResponse(**result)


@router.get("/providers")
def list_providers(
    settings: Settings = Depends(get_app_settings),
    _admin=Depends(get_current_admin),
):
    return {
        "configured_provider": settings.ai_provider,
        "configured_model": settings.ai_model,
        "api_key_set": bool(settings.ai_api_key),
        "base_url": settings.ai_base_url,
        "available_providers": [
            {"id": "deepseek", "label": "DeepSeek", "default_model": "deepseek-chat", "default_url": "https://api.deepseek.com/v1"},
            {"id": "ollama", "label": "Ollama (local)", "default_model": "llama3", "default_url": "http://localhost:11434/v1"},
            {"id": "openai", "label": "OpenAI", "default_model": "gpt-4o", "default_url": None},
        ],
    }
