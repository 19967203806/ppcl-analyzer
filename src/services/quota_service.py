import os
from datetime import datetime

from fastapi import HTTPException
from sqlmodel import select, func

from ..models import SessionDep
from ..models.usage import UsageEvent

# kind -> env var holding the per-user daily limit (unset or 0 = unlimited)
LIMIT_ENV = {
    "analysis": "DAILY_ANALYSIS_LIMIT",
    "chat": "DAILY_CHAT_LIMIT",
}


def _daily_limit(kind: str) -> int:
    raw = os.getenv(LIMIT_ENV[kind], "").strip()
    try:
        return max(int(raw), 0) if raw else 0
    except ValueError:
        return 0


class QuotaService:
    @staticmethod
    def consume(session: SessionDep, user_id: int, kind: str) -> None:
        """Record one request, or raise 429 if today's (UTC) limit is used up.

        Usage is recorded before the model runs, so failed or deleted analyses
        still count and cannot be used to bypass the limit.
        """
        limit = _daily_limit(kind)
        if limit:
            day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            used = session.exec(
                select(func.count()).select_from(UsageEvent).where(
                    UsageEvent.user_id == user_id,
                    UsageEvent.kind == kind,
                    UsageEvent.created_at >= day_start,
                )
            ).one()
            if used >= limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily {kind} limit reached ({limit} per day). Please try again tomorrow (UTC).",
                )
        session.add(UsageEvent(user_id=user_id, kind=kind))
        session.commit()
