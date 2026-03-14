"""SQLModel table definitions for persistent session and message storage."""

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, JSON
from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    id: str = Field(primary_key=True)
    state_json: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(sa_column=Column(sa.String, sa.ForeignKey("session.id", ondelete="CASCADE"), nullable=False, index=True))
    message_json: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    ordinal: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
