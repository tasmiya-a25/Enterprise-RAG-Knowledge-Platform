import io
import time


def _upload_txt(client, headers, filename="policy.txt", content=b"Acme Corp offers a 30-day return policy."):
    return client.post(
        "/api/v1/documents/upload", headers=headers,
        files={"file": (filename, io.BytesIO(content), "text/plain")},
    )


def _wait_until_indexed(client, headers, document_id, timeout=5):
    for _ in range(timeout * 10):
        r = client.get(f"/api/v1/documents/{document_id}", headers=headers)
        if r.json()["status"] in ("indexed", "failed"):
            return r.json()
        time.sleep(0.1)
    raise TimeoutError("document never finished processing")


def test_upload_rejects_unsupported_extension(client, auth_headers):
    r = client.post(
        "/api/v1/documents/upload", headers=auth_headers,
        files={"file": ("data.exe", io.BytesIO(b"binary"), "application/octet-stream")},
    )
    assert r.status_code == 400


def test_upload_txt_gets_indexed(client, auth_headers):
    r = _upload_txt(client, auth_headers)
    assert r.status_code == 201
    doc = r.json()
    assert doc["status"] == "pending"

    final = _wait_until_indexed(client, auth_headers, doc["id"])
    assert final["status"] == "indexed"
    assert final["indexed_at"] is not None


def test_list_documents_scoped_to_owner(client, auth_headers):
    _upload_txt(client, auth_headers)
    r = client.get("/api/v1/documents", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # A second user should see zero documents.
    client.post("/api/v1/auth/register", json={"email": "other@example.com", "password": "supersecret123"})
    other_login = client.post("/api/v1/auth/login", json={"email": "other@example.com", "password": "supersecret123"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    r = client.get("/api/v1/documents", headers=other_headers)
    assert r.json()["total"] == 0


def test_delete_document(client, auth_headers):
    r = _upload_txt(client, auth_headers)
    doc_id = r.json()["id"]
    _wait_until_indexed(client, auth_headers, doc_id)

    r = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert r.status_code == 404


def test_cannot_access_another_users_document(client, auth_headers):
    r = _upload_txt(client, auth_headers)
    doc_id = r.json()["id"]

    client.post("/api/v1/auth/register", json={"email": "other@example.com", "password": "supersecret123"})
    other_login = client.post("/api/v1/auth/login", json={"email": "other@example.com", "password": "supersecret123"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    r = client.get(f"/api/v1/documents/{doc_id}", headers=other_headers)
    assert r.status_code == 404
