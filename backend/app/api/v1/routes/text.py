# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import AdminDep, SettingsDep
from app.config import Settings
from app.schemas.text import TextGenerateRequest, TextGenerateResponse
from app.services.text import TextService

router = APIRouter(prefix="/text", tags=["text"])


@router.post("/generate", response_model=TextGenerateResponse)
async def generate_text(
    payload: TextGenerateRequest,
    settings: Settings = SettingsDep,
    _: None = AdminDep,
):
    """生成文本（非流式）"""
    service = TextService(settings)

    kwargs = {}
    if payload.messages:
        kwargs["messages"] = payload.messages

    text = await service.generate(
        prompt=payload.prompt,
        max_tokens=payload.max_tokens,
        temperature=payload.temperature,
        **kwargs,
    )

    return TextGenerateResponse(
        text=text,
        model=settings.text_model,
    )


@router.post("/stream")
async def stream_text(
    payload: TextGenerateRequest,
    settings: Settings = SettingsDep,
    _: None = AdminDep,
):
    """生成文本（流式）"""
    service = TextService(settings)

    kwargs = {}
    if payload.messages:
        kwargs["messages"] = payload.messages

    async def generate():
        async for chunk in service.stream(
            prompt=payload.prompt,
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
            **kwargs,
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")
