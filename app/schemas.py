from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class EventIn(BaseModel):
    timestamp: datetime
    user_id: str = Field(..., min_length=1)
    feature: str = Field(..., min_length=1)
    metadata: dict[str, Any] | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("timestamp must be a valid ISO 8601 datetime string")

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, v: Any) -> dict | None:
        import json

        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("metadata must be a JSON object (dict), not a list or primitive")

        def _check_depth(obj: Any, current: int = 1, max_depth: int = 2) -> None:
            if isinstance(obj, dict):
                if current > max_depth:
                    raise ValueError(
                        f"metadata exceeds maximum nesting depth of {max_depth} levels"
                    )
                for val in obj.values():
                    _check_depth(val, current + 1, max_depth)

        _check_depth(v)

        serialized = json.dumps(v)
        if len(serialized.encode("utf-8")) > 2048:
            raise ValueError(
                f"metadata size exceeds 2KB limit ({len(serialized.encode('utf-8'))} bytes). "
                "Keep metadata concise — it is telemetry, not a data store."
            )

        return v


class EventBatch(BaseModel):
    events: list[EventIn]

    @model_validator(mode="after")
    def check_batch_size(self) -> "EventBatch":
        from app.core.config import settings
        if len(self.events) > settings.MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size {len(self.events)} exceeds maximum allowed {settings.MAX_BATCH_SIZE}"
            )
        return self


class IngestResponse(BaseModel):
    ingested: int
    message: str


class UsageResponse(BaseModel):
    feature: str
    count: int
    start: datetime | None = None
    end: datetime | None = None


class UniqueUsersResponse(BaseModel):
    feature: str
    unique_users: int
    start: datetime | None = None
    end: datetime | None = None


class TopFeatureItem(BaseModel):
    feature: str
    count: int


class BreakdownItem(BaseModel):
    dimension_value: str | None
    count: int


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
