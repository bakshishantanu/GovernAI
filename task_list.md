# GovernAI: Two-Role Model & Admin Lockdown Implementation Task List

This task list tracks the execution of all phases outlined in `db_implementation_plan.md`.

## Phase 1: Core Role Definition Changes
- [x] **Task 1.1**: Update `app/api/schemas/auth.py`
  - Change `Role` literal type from `Literal["admin", "agent_builder", "user"]` to `Literal["admin", "agent_builder"]`.
- [x] **Task 1.2**: Update `app/domain/auth/middleware.py`
  - Remove `"dummy-token-user"` dev token branch.
  - Set default role to `"agent_builder"` in JWT parsing.
  - Map legacy `"user"` role to `"agent_builder"` and restrict allowed roles to `("admin", "agent_builder")`.
- [x] **Task 1.3**: Update `app/domain/auth/rbac.py`
  - Remove obsolete `require_user` dependency.
  - Update docstrings to reflect 2-role model.

## Phase 2: API Router Changes
- [x] **Task 2.1**: Update `app/api/v1/agents.py`
  - In `list_agents`: For `agent_builder`, set both `owner_id = user.id` and `assigned_user_id = user.id`. Remove `user` branch.
  - In `get_agent`: Check both `owner_id != user.id` and `assigned_user_id != user.id` for `agent_builder`.
  - Keep `submit_agent_for_review` and `activate_agent` restricted to `owner_id`.
- [x] **Task 2.2**: Update `app/api/v1/agent_requests.py`
  - In `create_request`: Change dependency to `require_builder_or_admin`.
  - In `list_requests`: Remove user-only scoping filter so builders see all requests in org.
  - In `get_request`: Remove user-only restriction so builders see any request in org.
  - In `cancel_request`: Use `require_builder_or_admin`, check `if user.role == "agent_builder" and req.requester_id != user.id`.
- [x] **Task 2.3**: Update `app/api/v1/executions.py`
  - In `create_and_run_execution`: Allow execution if `agent_builder` is owner OR assigned user.
  - In `list_executions`: Pass both `builder_id` and `assigned_user_id` for `agent_builder`.
  - In `get_execution_detail`: Allow detail view if `agent_builder` is owner OR assigned user.
- [x] **Task 2.4**: Update `app/api/v1/audits.py`
  - In `list_audit_events`: Pass both `builder_id` and `assigned_user_id` for `agent_builder`.

## Phase 3: Repository Layer Changes
- [x] **Task 3.1**: Update `app/domain/agents/repository.py`
  - In `list_agents_by_org` and `count_agents_by_org`: When both `owner_id` and `assigned_user_id` are set, apply `or_(Agent.owner_id == owner_id, Agent.assigned_user_id == assigned_user_id)`.
- [x] **Task 3.2**: Update `app/domain/executions/repository.py`
  - In `list_executions_for_org`: When both `builder_id` and `assigned_user_id` are set, apply `or_(Agent.owner_id == builder_id, Agent.assigned_user_id == assigned_user_id)`.
- [x] **Task 3.3**: Update `app/domain/audit/repository.py`
  - In `get_events_for_org`: Properly handle both `builder_id` and `assigned_user_id` being provided.

## Phase 4: Database Migration (Alembic + Supabase)
- [x] **Task 4.1**: Create Alembic migration script `merge_user_into_agent_builder`
  - Migrate data: `UPDATE profiles SET role = 'agent_builder' WHERE role = 'user'`.
  - Update CHECK constraint: `profiles_role_check` to `role IN ('admin', 'agent_builder')`.
  - Add downgrade logic.
- [x] **Task 4.2**: Run `uv run alembic upgrade head` and verify schema.
- [x] **Task 4.3**: Provide Supabase SQL script (`scripts/supabase_auth_hook.sql`) for `handle_new_user` trigger.

## Phase 5: Admin CLI Script
- [x] **Task 5.1**: Create `scripts/promote_to_admin.py`
  - Validate UUID CLI argument.
  - Update `Profile.role` to `'admin'`.
  - Update Supabase `auth.users.raw_app_meta_data` role claim if configured.

## Phase 6: Seed Data Updates
- [x] **Task 6.1**: Update `scripts/seed_demo_data.py`
  - Convert `user_id` profile from `"user"` to `"agent_builder"`.
  - Update comments and org/profile descriptions to reflect the 2-role model.

## Phase 7: Test Updates
- [x] **Task 7.1**: Update `tests/unit/test_rbac.py`
  - Update role assertions, verify `"user"` is rejected by `CurrentUser` model.
- [x] **Task 7.2**: Update `tests/unit/test_auth_middleware.py`
  - Update test payloads, add test for legacy `"user"` JWT claim mapping to `"agent_builder"`.
- [x] **Task 7.3**: Update `tests/test_agent_requests_api.py`
  - Change fixtures and assertions to reflect builder capabilities.
- [x] **Task 7.4**: Update `tests/test_three_role_governance.py`
  - Rewrite user-specific tests for merged permissions (own + assigned agents).
  - Add tests for builder creating requests and accessing assigned agents.

## Phase 8: Add New Admin-Only Tests & Full Suite Verification
- [x] **Task 8.1**: Create `tests/test_admin_lockdown.py`
  - Test admin registration lockdown (JWT defaults, dev token rejection for legacy user token).
  - Test `promote_to_admin.py` logic.
- [x] **Task 8.2**: Run full test suite (`uv run pytest tests/ -v`) and verify 100% green.
