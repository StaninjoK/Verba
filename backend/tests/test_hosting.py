import base64

import pytest

from verba.api import create_app

from .conftest import make_settings


def _auth(user, password):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


def test_refuses_to_start_without_password_when_required(tmp_path):
    with pytest.raises(RuntimeError):
        create_app(make_settings(tmp_path, require_auth=True, auth_password=""))


def test_basic_auth_protects_everything_but_health(build_client):
    client = build_client(auth_password="s3cret-pass")
    assert client.get("/api/health").status_code == 200
    denied = client.get("/api/projects")
    assert denied.status_code == 401 and "Basic" in denied.headers["www-authenticate"]
    assert client.get("/api/projects", headers=_auth("verba", "wrong")).status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Basic !!!"}).status_code == 401
    assert client.get("/api/projects", headers=_auth("verba", "s3cret-pass")).status_code == 200


def test_static_frontend_is_served_safely(build_client, tmp_path):
    static = tmp_path / "static"
    (static / "app").mkdir(parents=True)
    (static / "_next" / "static").mkdir(parents=True)
    (static / "index.html").write_text("<h1>home</h1>")
    (static / "app.html").write_text("<h1>library</h1>")
    (static / "app" / "project.html").write_text("<h1>project</h1>")
    (static / "_next" / "static" / "a.js").write_text("x")
    (static / "404.html").write_text("nope")
    (tmp_path / "secret.txt").write_text("secret")
    client = build_client(static_dir=static.resolve())
    assert client.get("/").text == "<h1>home</h1>"
    assert client.get("/app").text == "<h1>library</h1>"
    assert client.get("/app/project?id=abc").text == "<h1>project</h1>"
    assert "immutable" in client.get("/_next/static/a.js").headers["cache-control"]
    page = client.get("/app")
    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert client.get("/../secret.txt").status_code == 404
    assert client.get("/%2e%2e/secret.txt").status_code == 404
    assert client.get("/api/unknown").status_code == 404
    assert client.get("/api/health").json() == {"status": "ok"}
