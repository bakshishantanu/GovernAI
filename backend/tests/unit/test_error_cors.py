"""An unhandled server error must still reach the browser.

Starlette's ServerErrorMiddleware sits outside every user middleware, so a 500
it produces never passes back through CORSMiddleware and carries no
`Access-Control-Allow-Origin` header. The browser then rejects the response
before any JavaScript can read it and `fetch` rejects with "Failed to fetch" —
the status code and the message are both invisible in the console during
exactly the incident you most need them.

This happened for real: `POST /executions/` was raising MissingGreenlet and the
console could only report "Failed to fetch", which said nothing about the
actual fault.

`UnhandledErrorMiddleware` is registered inside CORS so the error response is
generated where CORS can still decorate it. These tests fail if that ordering
is ever reversed.
"""

from fastapi.testclient import TestClient

from app.main import app

ORIGIN = "http://localhost:3000"


def _client() -> TestClient:
    # raise_server_exceptions=False so the response is returned rather than the
    # exception being re-raised into the test.
    return TestClient(app, raise_server_exceptions=False)


def test_unhandled_error_is_json_not_a_bare_500(monkeypatch):
    @app.get("/__boom")
    async def boom():
        raise RuntimeError("something went wrong deep in a service")

    try:
        response = _client().get("/__boom", headers={"Origin": ORIGIN})

        assert response.status_code == 500
        body = response.json()
        assert body["data"] is None
        assert body["errors"][0]["status"] == 500
        assert body["errors"][0]["instance"] == "/__boom"
    finally:
        app.router.routes = [
            route for route in app.router.routes if getattr(route, "path", None) != "/__boom"
        ]


def test_unhandled_error_still_carries_the_cors_header():
    """The whole point: without this header the browser discards the response."""

    @app.get("/__boom2")
    async def boom2():
        raise RuntimeError("something went wrong deep in a service")

    try:
        response = _client().get("/__boom2", headers={"Origin": ORIGIN})

        assert response.status_code == 500
        assert response.headers.get("access-control-allow-origin") == ORIGIN
    finally:
        app.router.routes = [
            route for route in app.router.routes if getattr(route, "path", None) != "/__boom2"
        ]


def test_a_normal_response_is_unaffected():
    response = _client().get("/health", headers={"Origin": ORIGIN})

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.headers.get("access-control-allow-origin") == ORIGIN
