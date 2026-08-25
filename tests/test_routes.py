from anemiaiaback.api.routes import router


def test_capture_post_is_registered_in_routes_module():
    matches = [
        route
        for route in router.routes
        if route.path == "/api/v1/captures" and "POST" in route.methods
    ]
    assert len(matches) == 1
    assert matches[0].name == "create_capture_handler"
