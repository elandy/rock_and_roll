from datetime import datetime
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Podcast(Base):
    __tablename__ = "podcasts"

    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_id",
            name="uq_podcasts_source_source_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    author: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    feed_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    podcast_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    category: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    genres: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    color_palette: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )