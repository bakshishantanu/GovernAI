from __future__ import annotations
import uuid
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.domain.auth.middleware import get_current_user
from app.domain.auth.rbac import require_admin
from app.domain.auth.rbac import require_admin
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.policy import PolicyResponse, PolicyCreate, PolicyRuleCreate, PolicyRuleResponse
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
    current_user: CurrentUser = Depends(require_admin),
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


@router.get("/{policy_id}", response_model=Envelope[PolicyResponse])
async def get_policy(
    policy_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    repo: PolicyRepository = Depends(get_policy_repo),
):
    """One policy and its rules."""
    policy = await repo.get_policy(policy_id, current_user.org_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return Envelope(data=policy)


@router.patch("/{policy_id}", response_model=Envelope[PolicyResponse])
async def update_policy(
    policy_id: uuid.UUID,
    enabled: bool | None = Body(None, embed=True),
    name: str | None = Body(None, embed=True),
    description: str | None = Body(None, embed=True),
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    repo: PolicyRepository = Depends(get_policy_repo),
):
    """Rename a policy, or switch the whole thing on and off.

    Disabling a policy takes effect on the very next tool call — the engine
    reads rules from the database on every evaluation, so nothing needs
    redeploying (FRD-14).
    """
    policy = await repo.get_policy(policy_id, current_user.org_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")

    if enabled is not None:
        policy.enabled = enabled
    if name is not None:
        policy.name = name
    if description is not None:
        policy.description = description

    await db.commit()
    refreshed = await repo.get_policy(policy_id, current_user.org_id)
    return Envelope(data=refreshed)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    repo: PolicyRepository = Depends(get_policy_repo),
):
    """Remove a policy and its rules."""
    policy = await repo.get_policy(policy_id, current_user.org_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")

    await repo.delete_policy(policy)
    await db.commit()


@router.get("/{policy_id}/rules", response_model=Envelope[list[PolicyRuleResponse]])
async def list_rules(
    policy_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    repo: PolicyRepository = Depends(get_policy_repo),
):
    policy = await repo.get_policy(policy_id, current_user.org_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return Envelope(data=policy.rules)


@router.post(
    "/{policy_id}/rules",
    response_model=Envelope[PolicyRuleResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_rule(
    policy_id: uuid.UUID,
    rule_in: PolicyRuleCreate,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    repo: PolicyRepository = Depends(get_policy_repo),
):
    """Add a rule to an existing policy."""
    policy = await repo.get_policy(policy_id, current_user.org_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")

    rule = PolicyRule(
        id=uuid.uuid4(),
        policy_id=policy.id,
        name=rule_in.name,
        rule_type=rule_in.rule_type,
        config=rule_in.config,
        priority=rule_in.priority,
        enabled=rule_in.enabled,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return Envelope(data=rule)


@router.patch("/{policy_id}/rules/{rule_id}", response_model=Envelope[PolicyRuleResponse])
async def toggle_rule(
    policy_id: uuid.UUID,
    rule_id: uuid.UUID,
    enabled: bool = Body(..., embed=True),
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    repo: PolicyRepository = Depends(get_policy_repo),
):
    """Switch a single rule on or off.

    This is the endpoint behind FRD-14's acceptance test: turn a rule off and
    the same tool call that was refused a moment ago now goes through, with no
    restart. Rules are database rows, not compiled code, so the policy engine
    picks the change up on its next evaluation.
    """
    rule = await repo.get_rule(rule_id, current_user.org_id)
    if rule is None or rule.policy_id != policy_id:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.enabled = enabled
    await db.commit()
    await db.refresh(rule)
    return Envelope(data=rule)
