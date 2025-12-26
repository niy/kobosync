import pytest

from kobold.kepubify import KEPUBIFY_DOWNLOAD_BASE, KepubifyBinary


class TestKepubifyAvailability:
    @pytest.mark.asyncio
    async def test_kepubify_download_url_is_reachable(self):
        from kobold.http_client import HttpClientManager

        binary = KepubifyBinary()
        binary_name = binary._get_platform_binary_name()
        download_url = f"{KEPUBIFY_DOWNLOAD_BASE}/{binary_name}"

        client = await HttpClientManager.get_client()
        response = await client.head(download_url)

        assert response.status_code == 200, (
            f"Kepubify binary not available at {download_url}"
        )
