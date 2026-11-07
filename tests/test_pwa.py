"""Coverage for the progressive web app shell and worker endpoints."""


def test_manifest_is_linked_in_the_storefront(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b'rel="manifest"' in response.data
    assert b"/static/manifest.json" in response.data


def test_root_service_worker_is_available(client):
    response = client.get("/service-worker.js")

    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    assert b"self.addEventListener(\"fetch\"" in response.data