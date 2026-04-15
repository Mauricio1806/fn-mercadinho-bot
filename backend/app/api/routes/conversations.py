"""Rotas de conversas — visualização e controle pelo admin."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.middleware.auth import get_current_admin
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.conversation import Conversation, ConversationState, ConversationStatus
from app.models.message import Message, MessageDirection

router = APIRouter()


class MessageResponse(BaseModel):
    id: uuid.UUID
    direction: MessageDirection
    content: str
    is_ai_generated: bool
    tokens_used: int | None

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    status: ConversationStatus
    state: ConversationState
    message_count: int

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    status_filter: ConversationStatus | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[dict]:
    query = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    if status_filter:
        query = query.where(Conversation.status == status_filter)

    result = await db.execute(query)
    convs = result.scalars().all()

    return [
        {
            "id": c.id,
            "customer_id": c.customer_id,
            "status": c.status,
            "state": c.state,
            "message_count": len(c.messages),
        }
        for c in convs
    ]


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[Message]:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada."
        )

    return conv.messages


@router.post("/{conversation_id}/takeover")
async def human_takeover(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> dict:
    """Admin assume o controle da conversa (desativa o bot)."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada."
        )

    conv.status = ConversationStatus.HUMAN_TAKEOVER
    await db.commit()
    return {"status": "takeover", "conversation_id": str(conversation_id)}
