from unittest.mock import MagicMock, patch

import pytest

from kobosync.database import get_session


def test_get_session_commits_on_success():
    mock_session = MagicMock()
    with patch("kobosync.database.Session", return_value=mock_session):
        with get_session() as session:
            assert session == mock_session
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


def test_get_session_rollbacks_on_exception():
    mock_session = MagicMock()
    with patch("kobosync.database.Session", return_value=mock_session):
        with pytest.raises(ValueError), get_session():
            raise ValueError("Test Error")
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
