import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import settings
from app.infrastructure.rule_engine.audit_hook import AuditError
from app.infrastructure.rule_engine.core.engine import IngestionError
from app.services import rule_validation

router = APIRouter(tags=["streaming"])


def _check_api_key(api_key: str | None) -> bool:
    import hmac

    return bool(api_key and hmac.compare_digest(api_key, settings.api_key))


@router.websocket("/v1/ws/validate")
async def ws_validate(websocket: WebSocket, api_key: str = Query(default="")):
    if not _check_api_key(api_key):
        await websocket.close(code=4401, reason="Invalid API key")
        return
    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        body = json.loads(raw)
        claim = body.get("claim") if isinstance(body, dict) else None
        if not isinstance(claim, dict):
            await websocket.send_json({"type": "error", "message": "body must include claim object"})
            await websocket.close(code=4400)
            return

        try:
            response = rule_validation.validate_envelope(claim)
        except IngestionError as e:
            await websocket.send_json(
                {"type": "error", "error": "ingestion_error", "message": str(e), "details": e.details}
            )
            await websocket.close(code=4400)
            return
        except (AuditError, OSError) as e:
            await websocket.send_json({"type": "error", "error": "audit_unavailable", "message": str(e)})
            await websocket.close(code=4503)
            return

        for row in response.results:
            await websocket.send_json({"type": "rule", "result": row.model_dump(mode="json")})

        await websocket.send_json(
            {
                "type": "complete",
                "response": response.model_dump(mode="json"),
            }
        )
    except WebSocketDisconnect:
        return
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "message": "Invalid JSON"})
        await websocket.close(code=4400)
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
