import os
import shutil
import time
import zipfile
from collections.abc import Generator
from pathlib import Path

import httpx
import pymupdf
import pytest

BASE_URL = os.getenv("KB_TEST_URL", "http://localhost:8000")
TEST_TEMP_DIR = Path(".tmp/smoke_tests")
BOOKB_DIR = Path(os.getenv("KB_TEST_BOOKB_DIR", str(TEST_TEMP_DIR / "books")))
TOKEN = os.getenv("KB_USER_TOKEN", "dummy_token")
FETCH_METADATA = os.getenv("KB_TEST_FETCH_METADATA", "false").lower() == "true"


@pytest.fixture
def client() -> Generator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.mark.skipif(not FETCH_METADATA, reason="Metadata smoke test not enabled")
def test_metadata_extraction_end_to_end(client: httpx.Client) -> None:
    """
    E2E Metadata Test:
    1. Copy a known book (Romeo and Juliet) to the volume.
    2. Poll sync until it appears.
    3. Verify API returns enriched metadata (Goodreads/Amazon data).
    4. Download file and verify internal metadata/cover match.
    """
    assert BOOKB_DIR, "KB_TEST_BOOKB_DIR not set"
    books_path = Path(BOOKB_DIR)

    source_epub = Path("tests/data/romeo_and_juliet.epub")
    assert source_epub.exists(), "Source test file not found"

    target_name = "Romeo and Juliet - William Shakespeare.epub"
    dest_file = books_path / target_name
    if dest_file.exists():
        dest_file.unlink()

    shutil.copy(source_epub, dest_file)
    print(f"Copied book as {dest_file}")

    init_resp = client.get(f"/api/kobo/{TOKEN}/v1/initialization")
    assert init_resp.status_code == 200
    image_template = init_resp.json()["Resources"]["image_url_template"]

    book_id = None
    timeout = 180
    start_time = time.time()

    enriched_metadata = {}
    cover_verified = False

    while time.time() - start_time < timeout:
        try:
            resp = client.get(
                f"/api/kobo/{TOKEN}/v1/library/sync", headers={"X-Kobo-SyncToken": "0"}
            )
            assert resp.status_code == 200

            data = resp.json()
            for item in data:
                entitlement = item.get("NewEntitlement", {}) or item.get("Metadata", {})
                title = entitlement.get("Title", "")

                # Check for our book
                if "romeo" in title.lower() and "juliet" in title.lower():
                    book_id = entitlement.get("EntitlementId")
                    image_id = entitlement.get("ImageId")
                    desc = entitlement.get("Description", "")

                    print(
                        f"Polling: Found book '{title}'. Desc len: {len(desc) if desc else 0}"
                    )

                    if desc and len(desc) > 50:
                        enriched_metadata = entitlement

                        if image_id and image_template:
                            cover_url = (
                                image_template.replace("{ImageId}", image_id)
                                .replace("{Width}", "300")
                                .replace("{Height}", "450")
                            )

                            print(f"Verifying cover at: {cover_url}")
                            try:
                                img_resp = client.get(cover_url)
                                if (
                                    img_resp.status_code == 200
                                    and len(img_resp.content) > 0
                                ):
                                    print("Cover image verified.")
                                    cover_verified = True
                                    enriched_metadata["CoverVerified"] = True
                            except Exception as e:
                                print(f"Cover verification failed: {e}")

                        if cover_verified:
                            print(f"Found enriched metadata for: {title}")
                            break

            if enriched_metadata and cover_verified:
                break

        except Exception as e:
            print(f"Polling error: {e}")

        time.sleep(1)

    if not enriched_metadata and book_id:
        print(f"Timed out. Last seen metadata for book {book_id}:")

    assert book_id, "Timed out waiting for book to appear in sync"
    assert enriched_metadata.get("Description"), "Description was not updated"
    assert cover_verified, "Cover image could not be verified via template"

    print("API verification passed: Metadata appears enriched.")

    dl_resp = client.get(f"/download/{book_id}")
    assert dl_resp.status_code == 200

    downloaded_path = TEST_TEMP_DIR / "downloaded_romeo.epub"
    with downloaded_path.open("wb") as f:
        f.write(dl_resp.content)

    assert zipfile.is_zipfile(downloaded_path)

    with pymupdf.open(downloaded_path) as doc:
        meta = doc.metadata
        print(f"Downloaded file metadata: {meta}")

        assert "Romeo" in meta.get("title", ""), "File metadata title not updated"
        assert "Juliet" in meta.get("title", ""), "File metadata title not updated"
        assert "Shakespeare" in meta.get("author", ""), (
            "File metadata author not updated"
        )

    with zipfile.ZipFile(downloaded_path) as z:
        files = z.namelist()
        images = [
            f
            for f in files
            if f.endswith((".jpg", ".jpeg", ".png")) and "cover" in f.lower()
        ]
        assert images or any("cover" in f.lower() for f in files), (
            "No cover image found in downloaded EPUB"
        )

    print("File verification passed: File content metadata updated.")
