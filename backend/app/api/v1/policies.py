from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.domain.auth.middleware import get_current_user
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.policy import PolicyResponse, PolicyCreate
from app.domain.policies.repository import PolicyRepository
from app.domain.policies.models import Policy, PolicyRule

router = APIRouter(prefix="/policies", tags=["policies"])

def get_policy_repo(db: AsyncSession = Depends(get_db)) -> PolicyRepository:
    return PolicyRepository(db)


@router.get("/", response_model=Envelope[list[PolicyResponse]])
async def list_policies(
    current_user: CurrentUser = Depends(get_current_user),
    repo: PolicyRepository = Depends(get_policy_repo)
):
    """
    List all governance policies and their rules for the current user's organization.
    """
    policies = await repo.get_policies_for_org(current_user.org_id)
    return Envelope(data=policies)


@router.post("/", response_model=Envelope[PolicyResponse], status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy_in: PolicyCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: PolicyRepository = Depends(get_policy_repo)
):
    """
    Create a new governance policy with associated rules.
    """
    new_policy = Policy(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        name=policy_in.name,
        description=policy_in.description,
        enabled=policy_in.enabled
    )
    
    for rule_in in policy_in.rules:
        new_rule = PolicyRule(
            id=uuid.uuid4(),
            name=rule_in.name,
            rule_type=rule_in.rule_type,
            config=rule_in.config,
            priority=rule_in.priority,
            enabled=rule_in.enabled
        )
        new_policy.rules.append(new_rule)
        
    created_policy = await repo.create_policy(new_policy)
    await db.commit()
    await db.refresh(created_policy)
    
    return Envelope(data=created_policy)
