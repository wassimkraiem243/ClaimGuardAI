from fastapi import APIRouter, Depends, HTTPException

from app.deps import require_api_key
from app.services import rule_validation

router = APIRouter(
    prefix="/v1",
    tags=["rules"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/rules")
def list_rules():
    return rule_validation.list_rules_catalog()


@router.get("/policies/{policy_id}")
def get_policy(policy_id: str):
    policy = rule_validation.get_policy(policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="no matching policy supplied")
    return policy
