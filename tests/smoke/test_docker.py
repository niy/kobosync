import io
import os
import shutil
import time
import zipfile
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest

BASE_URL = os.getenv("KB_TEST_URL", "http://localhost:8000")
TEST_TEMP_DIR = Path(".tmp/smoke_tests")
BOOKB_DIR = Path(os.getenv("KB_TEST_BOOKB_DIR", str(TEST_TEMP_DIR / "books")))
DATA_DIR = Path(os.getenv("KB_TEST_DATA_DIR", str(TEST_TEMP_DIR / "data")))
TOKEN = os.getenv("KB_USER_TOKEN", "dummy_token")


@pytest.fixture
def client() -> Generator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


def test_health_check(client: httpx.Client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unauthorized_access(client: httpx.Client) -> None:
    resp = client.get("/api/kobo/invalid_token/v1/library/sync")
    assert resp.status_code in (401, 403)


def test_e2e_sync_flow(client: httpx.Client) -> None:
    """
    E2E Test:
    1. Create a dummy EPUB file in the shared volume.
    2. Poll the sync endpoint until the book appears.
    3. Download the book and verify it.
    """
    assert BOOKB_DIR, "KB_TEST_BOOKB_DIR not set, cannot run E2E file test"

    books_path = Path(BOOKB_DIR)
    assert books_path.exists(), f"Books directory {BOOKB_DIR} does not exist"

    # 1. Copy real EPUB to the shared volume
    source_dir = Path("tests/data")
    epub_name = "romeo_and_juliet.epub"
    source_file = source_dir / epub_name

    assert source_file.exists(), f"Source file {source_file} not found"

    dest_file = books_path / epub_name
    shutil.copy(source_file, dest_file)

    print(f"Copied book to {dest_file}")

    # 2. Poll for the book
    book_id = None
    timeout = 30  # seconds
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            resp = client.get(
                f"/api/kobo/{TOKEN}/v1/library/sync", headers={"X-Kobo-SyncToken": "0"}
            )

            assert resp.status_code == 200, (
                f"Sync endpoint returned status {resp.status_code}: {resp.text}"
            )

            data = resp.json()
            found = False
            for item in data:
                entitlement = item.get("NewEntitlement", {})
                if not entitlement:
                    entitlement = item.get("Metadata", {})

                if "romeo" in entitlement.get("Title", "").lower():
                    book_id = entitlement.get("EntitlementId")
                    found = True
                    print(f"Found book in sync response: {entitlement.get('Title')}")
                    break

            if found:
                break

            print(f"Book not found yet. Items returned: {len(data)}")

        except httpx.RequestError as e:
            pytest.fail(f"Connection failed during polling: {e}")

        time.sleep(0.2)

    assert book_id, "Timed out waiting for book to be synced"

    print(f"Book synced with ID: {book_id}")

    # 3. Verify Download
    dl_resp = client.get(f"/download/{book_id}")
    assert dl_resp.status_code == 200, (
        f"Download failed with status {dl_resp.status_code}"
    )

    assert dl_resp.headers["content-type"] == "application/epub+zip"
    assert len(dl_resp.content) > 0
    assert zipfile.is_zipfile(io.BytesIO(dl_resp.content)), (
        "Downloaded file is not a valid zip/epub"
    )

    with zipfile.ZipFile(io.BytesIO(dl_resp.content)) as z:
        assert "mimetype" in z.namelist(), "Valid EPUB/KEPUB must have a mimetype file"
        assert z.read("mimetype").decode("utf-8").strip() == "application/epub+zip", (
            "Invalid mimetype in EPUB"
        )
    print("Downloaded file verified as valid EPUB/KEPUB")
