from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.db.session import get_db
from app.services.export import iter_podcast_ndjson

router = APIRouter(
    prefix="/export",
    tags=["Export"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "/podcasts",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/x-ndjson": {
                    "example": (
                        '{"id":"...","title":"Rock Feed"}\n'
                        '{"id":"...","title":"Rock Weekly"}'
                    )
                }
            }
        }
    },
)
def export_podcasts(
    db: Session = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        iter_podcast_ndjson(db),
        media_type="application/x-ndjson",
    )