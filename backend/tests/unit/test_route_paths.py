"""Guards the shape of the public API surface.

Four routers once declared their own prefix *and* were mounted under the same
prefix again in `main.py`, so they were served at `/api/v1/skills/skills/`,
`/api/v1/policies/policies/` and so on. Only `agents` was correct, which is why
the agents page worked and nothing else did. Any frontend call to the documented
path returned 404.

These tests exist so that never silently happens again.
"""

from app.main import app

EXPECTED_PATHS = {
    "/api/v1/agents/",
    "/api/v1/agents/{agent_id}",
    "/api/v1/agents/{agent_id}/submit",
    "/api/v1/agents/{agent_id}/activate",
    "/api/v1/agents/{agent_id}/kill",
    "/api/v1/agents/{agent_id}/reactivate",
    "/api/v1/skills/",
    "/api/v1/skills/{skill_id}",
    "/api/v1/policies/",
    "/api/v1/audits/",
    "/api/v1/executions/",
    "/api/v1/executions/{execution_id}",
    "/api/v1/executions/{execution_id}/cancel",
    "/api/v1/executions/{execution_id}/stream",
    "/api/v1/costs/",
    "/api/v1/costs/summary",
    "/api/v1/costs/budget",
    "/api/v1/automations/",
    "/api/v1/automations/{automation_id}",
    "/api/v1/automation-runs/",
    "/api/v1/auth/me",
    "/api/v1/auth/settings",
    "/api/v1/events/stream",
    "/api/v1/policies/{policy_id}",
    "/api/v1/policies/{policy_id}/rules",
    "/api/v1/policies/{policy_id}/rules/{rule_id}",
}


def api_paths() -> set[str]:
    return {
        path
        for path in app.openapi()["paths"].keys()
        if path.startswith("/api/v1")
    }

def test_no_path_segment_is_repeated():
    """`/api/v1/skills/skills/` is the exact failure this catches."""
    for path in api_paths():
        segments = [s for s in path.split("/") if s and not s.startswith("{")]
        duplicated = [s for s in set(segments) if segments.count(s) > 1]
        assert not duplicated, f"{path} repeats {duplicated}"

def test_every_expected_route_is_mounted_where_the_frontend_expects_it():
    missing = EXPECTED_PATHS - api_paths()
    assert not missing, f"routes missing or moved: {sorted(missing)}"

def test_every_api_route_lives_under_the_version_prefix():
    for path in app.openapi()["paths"].keys():
        if path.startswith(("/docs", "/redoc", "/openapi", "/health", "/api/v1")):
            continue
        # If it doesn't match the standard prefixes, it must start with /api/v1
        assert path.startswith("/api/v1"), f"{path} is outside the versioned API"


def test_a_static_segment_never_sits_where_an_id_is_expected():
    """`PATCH /policies/rules/{id}` would be swallowed by `PATCH /policies/{id}`,
    which matches first and then fails UUID validation. Nesting the rule under
    its policy avoids the ambiguity; this catches a regression."""
    id_holders: dict[tuple[str, int], set[str]] = {}
    for path in api_paths():
        segments = path.strip("/").split("/")
        for index, segment in enumerate(segments):
            prefix = "/".join(segments[:index])
            key = (prefix, index)
            id_holders.setdefault(key, set()).add(
                "PARAM" if segment.startswith("{") else segment
            )

    for (prefix, index), variants in id_holders.items():
        if "PARAM" in variants and len(variants) > 1:
            static = sorted(variants - {"PARAM"})
            raise AssertionError(
                f"at /{prefix} position {index}, static {static} competes with a "
                f"path parameter — the parameter route may shadow it"
            )
