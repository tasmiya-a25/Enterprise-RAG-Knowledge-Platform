import io
import time


def _upload_and_wait(client, headers, content):
    r = client.post(
        "/api/v1/documents/upload", headers=headers,
        files={"file": ("policy.txt", io.BytesIO(content), "text/plain")},
    )
    doc_id = r.json()["id"]
    for _ in range(50):
        status = client.get(f"/api/v1/documents/{doc_id}", headers=headers).json()["status"]
        if status in ("indexed", "failed"):
            assert status == "indexed"
            return doc_id
        time.sleep(0.1)
    raise TimeoutError("document never finished processing")


def test_chat_with_no_documents_admits_lack_of_info(client, auth_headers):
    r = client.post("/api/v1/chat", headers=auth_headers, json={"message": "What is the return policy?"})
    assert r.status_code == 200
    body = r.json()["message"]
    assert body["citations"] == []
    assert "don't have enough information" in body["content"]


def test_chat_answers_from_uploaded_document_with_citation(client, auth_headers):
    content = b"Acme Corp offers a 30-day return policy on all electronics."
    _upload_and_wait(client, auth_headers, content)

    r = client.post("/api/v1/chat", headers=auth_headers, json={"message": "What is the return policy?"})
    assert r.status_code == 200
    message = r.json()["message"]
    assert len(message["citations"]) >= 1
    assert message["citations"][0]["document_name"] == "policy.txt"


def test_chat_persists_history_across_turns(client, auth_headers):
    content = b"Acme Corp offers a 30-day return policy on all electronics."
    _upload_and_wait(client, auth_headers, content)

    r1 = client.post("/api/v1/chat", headers=auth_headers, json={"message": "What is the return policy?"})
    chat_id = r1.json()["chat_id"]

    r2 = client.post("/api/v1/chat", headers=auth_headers,
                      json={"message": "And for how long?", "chat_id": chat_id})
    assert r2.json()["chat_id"] == chat_id

    history = client.get(f"/api/v1/chat/{chat_id}", headers=auth_headers)
    assert history.status_code == 200
    # 2 user turns + 2 assistant turns
    assert len(history.json()["messages"]) == 4


def test_chat_history_list_and_delete(client, auth_headers):
    content = b"Acme Corp offers a 30-day return policy on all electronics."
    _upload_and_wait(client, auth_headers, content)
    r = client.post("/api/v1/chat", headers=auth_headers, json={"message": "Hello?"})
    chat_id = r.json()["chat_id"]

    r = client.get("/api/v1/chat/history", headers=auth_headers)
    assert r.status_code == 200
    assert any(c["id"] == chat_id for c in r.json())

    r = client.delete(f"/api/v1/chat/{chat_id}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/api/v1/chat/{chat_id}", headers=auth_headers)
    assert r.status_code == 404


def test_feedback_submission(client, auth_headers):
    content = b"Acme Corp offers a 30-day return policy on all electronics."
    _upload_and_wait(client, auth_headers, content)
    r = client.post("/api/v1/chat", headers=auth_headers, json={"message": "return policy?"})
    message_id = r.json()["message"]["id"]

    r = client.post("/api/v1/feedback", headers=auth_headers, json={"message_id": message_id, "rating": 1})
    assert r.status_code == 201
