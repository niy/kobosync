from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlmodel import Session

from kobold.models import Book
from kobold.services.metadata_service import MetadataJobService


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def mock_engine():
    return Mock()


@pytest.fixture
def mock_settings():
    return Mock()


@pytest.fixture
def mock_manager():
    return Mock()


@pytest.fixture
def metadata_service(mock_settings, mock_engine, mock_manager):
    return MetadataJobService(mock_settings, mock_engine, mock_manager)


@pytest.mark.asyncio
async def test_process_job_updates_metadata(
    metadata_service, mock_session, mock_manager, mock_engine
):
    book_id = "123e4567-e89b-12d3-a456-426614174000"

    mock_book = MagicMock(spec=Book)
    mock_book.id = book_id
    mock_book.title = "Old Title"
    mock_book.author = "Old Author"
    mock_book.file_path = "/path/book.epub"
    mock_book.isbn13 = None
    mock_book.isbn10 = None
    mock_book.isbn = None

    mock_session_instance = MagicMock(spec=Session)
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.get.return_value = mock_book

    mock_manager.get_metadata = AsyncMock(
        return_value={
            "title": "New Title",
            "author": "New Author",
            "description": "A great book",
        }
    )

    with patch("kobold.services.metadata_service.Session", mock_session):
        await metadata_service.process_job({"book_id": book_id})

        assert mock_book.title == "New Title"
        assert mock_book.author == "New Author"
        mock_book.mark_updated.assert_called_once()
        mock_session_instance.add.assert_called_with(mock_book)
        mock_session_instance.commit.assert_called_once()


@pytest.mark.asyncio
async def test_process_job_ignores_missing_book_id(metadata_service):
    await metadata_service.process_job({"some_other_field": "value"})

    metadata_service.metadata_manager.get_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_process_job_ignores_non_existent_book(metadata_service, mock_session):
    book_id = "123e4567-e89b-12d3-a456-426614174000"
    mock_session_instance = MagicMock(spec=Session)
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.get.return_value = None

    with patch("kobold.services.metadata_service.Session", mock_session):
        await metadata_service.process_job({"book_id": book_id})

    metadata_service.metadata_manager.get_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_process_job_handles_no_metadata_found(
    metadata_service, mock_session, mock_manager
):
    book_id = "123e4567-e89b-12d3-a456-426614174000"
    mock_book = MagicMock(spec=Book)
    mock_book.id = book_id
    mock_book.isbn13 = None
    mock_book.isbn10 = None
    mock_book.isbn = None

    mock_session_instance = MagicMock(spec=Session)
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.get.return_value = mock_book

    mock_manager.get_metadata = AsyncMock(return_value=None)

    with patch("kobold.services.metadata_service.Session", mock_session):
        await metadata_service.process_job({"book_id": book_id})

    mock_session_instance.add.assert_not_called()
    mock_session_instance.commit.assert_not_called()


@pytest.mark.asyncio
async def test_process_job_handles_no_updated_fields(
    metadata_service, mock_session, mock_manager
):
    book_id = "123e4567-e89b-12d3-a456-426614174000"
    mock_book = MagicMock(spec=Book)
    mock_book.id = book_id

    mock_session_instance = MagicMock(spec=Session)
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.get.return_value = mock_book

    mock_book.title = "Existing Title"

    # Metadata matches existing book
    mock_manager.get_metadata = AsyncMock(return_value={"title": "Existing Title"})

    with patch("kobold.services.metadata_service.Session", mock_session):
        await metadata_service.process_job({"book_id": book_id})

    # Should not attempt to update book since values are identical
    mock_session_instance.add.assert_not_called()
    mock_session_instance.commit.assert_not_called()


@pytest.mark.asyncio
async def test_process_job_ignores_unknown_fields(
    metadata_service, mock_session, mock_manager
):
    book_id = "123e4567-e89b-12d3-a456-426614174000"
    mock_book = MagicMock(spec=Book)
    mock_book.id = book_id
    mock_book.isbn13 = None
    mock_book.isbn10 = None
    mock_book.isbn = None

    mock_session_instance = MagicMock(spec=Session)
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.get.return_value = mock_book

    mock_manager.get_metadata = AsyncMock(return_value={"unknown_field": "some value"})

    with patch("kobold.services.metadata_service.Session", mock_session):
        await metadata_service.process_job({"book_id": book_id})

    mock_session_instance.add.assert_not_called()
    mock_session_instance.commit.assert_not_called()


@pytest.mark.asyncio
async def test_process_job_handles_cover_download_failure(
    metadata_service, mock_session, mock_manager
):
    book_id = "123e4567-e89b-12d3-a456-426614174000"
    metadata_service.settings.EMBED_METADATA = True

    mock_book = Mock(spec=Book)
    mock_book.file_path = "/path/book.epub"
    mock_book.isbn13 = None
    mock_book.isbn10 = None
    mock_book.isbn = None

    mock_session_instance = MagicMock(spec=Session)
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.get.return_value = mock_book

    mock_manager.get_metadata = AsyncMock(
        return_value={
            "title": "Title",
            "cover_path": "http://example.com/cover.jpg",
        }
    )

    mock_client = AsyncMock()
    mock_client.get.return_value.status_code = 404

    with (
        patch("kobold.services.metadata_service.Session", mock_session),
        patch(
            "kobold.services.metadata_service.HttpClientManager.get_client",
            AsyncMock(return_value=mock_client),
        ),
    ):
        await metadata_service.process_job({"book_id": book_id})

    # verify embed_metadata called WITHOUT cover_data
    call_args = mock_manager.embed_metadata.call_args
    assert call_args is not None
    args, _ = call_args
    assert "cover_data" not in args[1]


@pytest.mark.asyncio
async def test_process_job_handles_cover_download_exception(
    metadata_service, mock_session, mock_manager
):
    book_id = "123e4567-e89b-12d3-a456-426614174000"
    metadata_service.settings.EMBED_METADATA = True

    mock_book = Mock(spec=Book)
    mock_book.id = book_id
    mock_book.file_path = "/path/book.epub"
    mock_book.isbn13 = None
    mock_book.isbn10 = None
    mock_book.isbn = None

    mock_session_instance = MagicMock(spec=Session)
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.get.return_value = mock_book

    mock_manager.get_metadata = AsyncMock(
        return_value={
            "title": "Title",
            "cover_path": "http://example.com/cover.jpg",
        }
    )

    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Network Error")

    with (
        patch("kobold.services.metadata_service.Session", mock_session),
        patch(
            "kobold.services.metadata_service.HttpClientManager.get_client",
            AsyncMock(return_value=mock_client),
        ),
    ):
        await metadata_service.process_job({"book_id": book_id})

    mock_manager.embed_metadata.assert_called_once()
    call_args = mock_manager.embed_metadata.call_args
    args, _ = call_args
    assert "cover_data" not in args[1]


@pytest.mark.asyncio
async def test_process_job_embeds_metadata(
    metadata_service, mock_session, mock_manager, mock_engine
):
    book_id = "123e4567-e89b-12d3-a456-426614174000"

    metadata_service.settings.EMBED_METADATA = True

    mock_book = Mock(spec=Book)
    mock_book.file_path = "/path/book.epub"
    mock_book.isbn13 = None
    mock_book.isbn10 = None
    mock_book.isbn = None

    mock_session_instance = MagicMock(spec=Session)
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.get.return_value = mock_book

    mock_manager.get_metadata = AsyncMock(
        return_value={"title": "Title", "cover_path": "http://example.com/cover.jpg"}
    )

    mock_client = AsyncMock()
    mock_client.get.return_value.status_code = 200
    mock_client.get.return_value.content = b"cover_data"

    with (
        patch("kobold.services.metadata_service.Session", mock_session),
        patch(
            "kobold.services.metadata_service.HttpClientManager.get_client",
            AsyncMock(return_value=mock_client),
        ),
    ):
        await metadata_service.process_job({"book_id": book_id})

        expected_metadata = {
            "title": "Title",
            "cover_path": "http://example.com/cover.jpg",
            "cover_data": b"cover_data",
        }
        mock_manager.embed_metadata.assert_called_once_with(
            "/path/book.epub", expected_metadata
        )
