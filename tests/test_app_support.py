"""Application-wide error handlers and template context helpers."""
from flask import abort


def test_not_found_page_uses_central_error_handler(client):
    response = client.get("/not-a-real-page")
    assert response.status_code == 404
    assert b"requested page could not be found" in response.data


def test_cart_context_counts_quantities_not_distinct_products(client):
    with client.session_transaction() as browser_session:
        browser_session["cart"] = {"4": 3, "8": {"quantity": 2, "unit_price": "1"}}
    response = client.get("/")
    assert response.status_code == 200
    assert b">5</span>" in response.data


def test_validation_error_handler_returns_bad_request(app, client):
    @app.get("/test-validation-error")
    def invalid_request():
        raise ValueError("Invalid test input")

    response = client.get("/test-validation-error")
    assert response.status_code == 400
    assert b"Invalid test input" in response.data


def test_internal_error_handler_hides_exception_details(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/test-internal-error")
    def internal_failure():
        raise RuntimeError("private implementation detail")

    response = client.get("/test-internal-error")
    assert response.status_code == 500
    assert b"unexpected error occurred" in response.data
    assert b"private implementation detail" not in response.data