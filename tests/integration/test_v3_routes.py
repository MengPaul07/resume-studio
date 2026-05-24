from src.main import app


def _route_paths() -> set[str]:
    return {str(getattr(route, "path", "")) for route in app.router.routes}


def test_v3_core_routes_exposed():
    paths = _route_paths()
    assert "/api/v1/agent/v3/sessions" in paths
    assert "/api/v1/agent/v3/sessions/{session_id}" in paths
    assert "/api/v1/agent/v3/sessions/{session_id}/turns:run" in paths
    assert "/api/v1/agent/v3/sessions/{session_id}/actions:apply" in paths
    assert "/api/v1/agent/v3/sessions/{session_id}/actions:reject" in paths
    assert "/api/v1/agent/v3/sessions/{session_id}/rollback" in paths


def test_no_public_v2_routes_registered():
    paths = _route_paths()
    assert not any("/agent/v2/" in path for path in paths)


def test_import_recent_resource_routes_exposed():
    paths = _route_paths()
    assert "/api/v1/agent/import-file" in paths
    assert "/api/v1/agent/run-import" in paths
    assert "/api/v1/agent/imports" in paths
    assert "/api/v1/agent/recent-resumes" in paths
    assert "/api/v1/agent/recent-resumes/save" in paths
