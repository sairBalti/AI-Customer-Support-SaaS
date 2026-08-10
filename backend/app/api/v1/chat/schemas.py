"""Chat API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateConversationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    language: str = Field(default="en", max_length=20)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)


class ChatSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    document_name: str
    chunk_id: int | None = None
    chunk_uuid: str | None = None
    page: int | None = None
    score: float


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: int
    conversation_uuid: str
    company_id: int
    customer_id: int
    title: str | None = None
    language: str
    status: str
    total_messages: int
    ai_provider: str
    ai_model: str
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    message_uuid: str
    conversation_id: int
    company_id: int
    sender_type: str
    message_type: str
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    ai_provider: str | None = None
    ai_model: str | None = None
    created_at: datetime


class SendMessageResponse(BaseModel):
    answer: str
    sources: list[ChatSourceResponse]
    used_knowledge: bool
    conversation: ConversationResponse
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
