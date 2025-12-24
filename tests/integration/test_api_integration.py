from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from kobosync.main import app
from kobosync.models import Book


def test_auth_check(integration_ctx):
    client = TestClient(app)
    token = "test_token"

    response = client.post(f"/api/kobo/{token}/v1/auth/device", json={})
    assert response.status_code == 200
    assert "AccessToken" in response.json()


def test_sync_flow(integration_ctx):
    ctx = integration_ctx
    client = TestClient(app)
    token = "test_token"

    response = client.get(
        f"/api/kobo/{token}/v1/library/sync", headers={"x-kobo-synctoken": "0"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

    book_file = ctx.watch_dir / "test_book.epub"
    book_file.write_text("dummy content")

    with Session(ctx.engine) as session:
        book = Book(
            title="Test Book",
            author="Test Author",
            file_path=str(book_file),
            file_hash="abc123hash",
            file_size=1024,
            file_format="epub",
            isbn="9780000000001",
        )
        session.add(book)
        session.commit()
        session.refresh(book)
        book_id = str(book.id)

    response = client.get(
        f"/api/kobo/{token}/v1/library/sync", headers={"x-kobo-synctoken": "0"}
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    item = data[0]
    expected_entitlement = item.get("NewEntitlement", {})
    assert expected_entitlement.get("Title") == "Test Book"
    assert expected_entitlement.get("EntitlementId") == book_id

    next_token = response.headers.get("x-kobo-synctoken")
    assert next_token is not None
    response = client.get(
        f"/api/kobo/{token}/v1/library/sync", headers={"x-kobo-synctoken": next_token}
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

    with Session(ctx.engine) as session:
        b = session.get(Book, UUID(book_id))
        if b:
            b.mark_deleted()
            session.add(b)
            session.commit()

    response = client.get(
        f"/api/kobo/{token}/v1/library/sync", headers={"x-kobo-synctoken": next_token}
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert "RemoveEntitlement" in data[0]
    assert data[0]["RemoveEntitlement"]["EntitlementId"] == book_id


def test_download_book(integration_ctx):
    ctx = integration_ctx
    client = TestClient(app)

    book_content = b"Binary Book Content"
    book_file = ctx.watch_dir / "download_test.epub"
    book_file.write_bytes(book_content)

    with Session(ctx.engine) as session:
        book = Book(
            title="Download Me",
            file_path=str(book_file),
            file_hash="downloadhash",
            file_size=len(book_content),
            file_format="epub",
        )
        session.add(book)
        session.commit()
        book_id = str(book.id)

    response = client.get(f"/download/{book_id}")
    assert response.status_code == 200
    assert response.content == book_content
    assert response.headers["content-type"] == "application/epub+zip"
