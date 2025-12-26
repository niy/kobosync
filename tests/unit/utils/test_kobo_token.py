import base64
import json

from kobold.utils.kobo_token import KoboSyncToken


class TestKoboSyncToken:
    def test_default_values(self) -> None:
        """Test that default values are None."""
        token = KoboSyncToken()

        assert token.lastSuccessfulSyncPointId is None
        assert token.ongoingSyncPointId is None
        assert token.rawKoboSyncToken is None

    def test_with_values(self) -> None:
        token = KoboSyncToken(
            lastSuccessfulSyncPointId="2024-01-01T00:00:00",
            rawKoboSyncToken="raw_token_here",
        )

        assert token.lastSuccessfulSyncPointId == "2024-01-01T00:00:00"
        assert token.ongoingSyncPointId is None
        assert token.rawKoboSyncToken == "raw_token_here"

    def test_to_base64_empty_token(self) -> None:
        token = KoboSyncToken()

        result = token.to_base64()

        decoded = base64.b64decode(result).decode("utf-8")
        data = json.loads(decoded)

        assert data["lastSuccessfulSyncPointId"] is None
        assert data["ongoingSyncPointId"] is None
        assert data["rawKoboSyncToken"] is None

    def test_to_base64_with_values(self) -> None:
        token = KoboSyncToken(
            lastSuccessfulSyncPointId="2024-06-15T12:00:00",
            rawKoboSyncToken="upstream_token",
        )

        result = token.to_base64()

        decoded = base64.b64decode(result).decode("utf-8")
        data = json.loads(decoded)

        assert data["lastSuccessfulSyncPointId"] == "2024-06-15T12:00:00"
        assert data["rawKoboSyncToken"] == "upstream_token"

    def test_from_base64_valid_token(self) -> None:
        data = {
            "lastSuccessfulSyncPointId": "2024-01-01T00:00:00",
            "ongoingSyncPointId": None,
            "rawKoboSyncToken": "test_raw",
        }
        encoded = base64.b64encode(json.dumps(data).encode()).decode()

        result = KoboSyncToken.from_base64(encoded)

        assert result.lastSuccessfulSyncPointId == "2024-01-01T00:00:00"
        assert result.rawKoboSyncToken == "test_raw"

    def test_from_base64_invalid_base64(self) -> None:
        result = KoboSyncToken.from_base64("not valid base64!!!")

        assert result.lastSuccessfulSyncPointId is None
        assert result.rawKoboSyncToken is None

    def test_from_base64_invalid_json(self) -> None:
        invalid_json = base64.b64encode(b"not json").decode()

        result = KoboSyncToken.from_base64(invalid_json)

        assert result.lastSuccessfulSyncPointId is None

    def test_roundtrip(self) -> None:
        original = KoboSyncToken(
            lastSuccessfulSyncPointId="2024-03-15T08:30:00.123456",
            ongoingSyncPointId="ongoing",
            rawKoboSyncToken="raw_upstream_token_value",
        )

        encoded = original.to_base64()
        decoded = KoboSyncToken.from_base64(encoded)

        assert decoded.lastSuccessfulSyncPointId == original.lastSuccessfulSyncPointId
        assert decoded.ongoingSyncPointId == original.ongoingSyncPointId
        assert decoded.rawKoboSyncToken == original.rawKoboSyncToken

    def test_from_base64_empty_string(self) -> None:
        result = KoboSyncToken.from_base64("")

        assert result.lastSuccessfulSyncPointId is None
