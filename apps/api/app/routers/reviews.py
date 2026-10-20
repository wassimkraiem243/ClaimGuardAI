from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.deps import Principal, require_api_key, require_reviewer
from app.infrastructure.audit_log import REVIEW_ACTIONS
from app.services.review_routing import ReviewDecisionRequest, RouteResponse, route_claim, submit_decision

router = APIRouter(prefix="/v1/reviews", tags=["reviews"])


@router.get("/actions", dependencies=[Depends(require_api_key)])
def list_review_actions():
    return {"actions": sorted(REVIEW_ACTIONS)}


@router.post("/route", response_model=RouteResponse, dependencies=[Depends(require_api_key)])
def post_review_route(body: dict[str, Any]):
    claim = body.get("claim")
    if not isinstance(claim, dict):
        raise HTTPException(422, "body.claim must be a claim envelope object")
    return route_claim(claim)


@router.post("/decisions")
def post_review_decision(body: ReviewDecisionRequest, principal: Principal = Depends(require_reviewer)):
    try:
        return submit_decision(principal.actor, body)
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from e
