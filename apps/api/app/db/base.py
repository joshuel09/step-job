"""Declarative base and the mixins every entity carries.

The UUID primary key is not a style choice: FR-010 requires every entry be
individually addressable so that any claim in a generated document can be traced
back to what supports it (constitution gate G3).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKey:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Entity(Base, UUIDPrimaryKey, Timestamps):
    """Every persisted entity in the career module."""

    __abstract__ = True
