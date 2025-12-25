from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kobosync.metadata.amazon import AmazonProvider


class TestAmazonProvider:
    @pytest.fixture
    def provider(self) -> AmazonProvider:
        mock_settings = MagicMock()
        mock_settings.AMAZON_DOMAIN = "com"
        mock_settings.AMAZON_COOKIE = None
        return AmazonProvider(settings=mock_settings)

    @pytest.mark.asyncio
    async def test_fetch_metadata_success(self, provider: AmazonProvider) -> None:
        mock_search_html = """
        <html>
        <div data-component-type="s-search-result" class="s-result-item s-asin">
            <div class="sg-col-inner">
                <div class="s-widget-container">
                    <span class="a-declarative">
                        <div class="puis-card-container s-card-container">
                            <div class="a-section">
                                <div class="sg-row">
                                    <div class="sg-col sg-col-4-of-12 sg-col-8-of-16 sg-col-12-of-20 s-list-col-right">
                                        <div class="sg-col-inner">
                                            <div class="a-section a-spacing-small a-spacing-top-small">
                                                <h2 class="a-size-mini a-spacing-none a-color-base s-line-clamp-2">
                                                    <a class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal" href="/dp/B001234567">
                                                        <span class="a-size-medium a-color-base a-text-normal">Book Result</span>
                                                    </a>
                                                </h2>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </span>
                </div>
            </div>
        </div>
        </html>
        """

        mock_detail_html = """
        <html>
        <div id="dp-container" class="a-container">
            <div id="centerCol" class="centerColAlign">
                <div id="title_feature_div" class="celwidget">
                    <div class="a-section a-spacing-none">
                        <h1 id="title" class="a-spacing-none a-text-normal">
                            <span id="productTitle" class="a-size-large celwidget">Test Book Title</span>
                        </h1>
                    </div>
                </div>
                <div id="bylineInfo_feature_div" class="celwidget">
                    <div id="bylineInfo" class="a-section a-spacing-micro bylineHidden feature">
                        <span class="author notFaded">
                            <a class="a-link-normal" href="/author/Test-Author">Test Author</a>
                            <span class="contribution"><span class="a-color-secondary">(Author)</span></span>
                        </span>
                    </div>
                </div>
                <div id="averageCustomerReviews_feature_div">
                    <span id="acrPopover" class="reviewCountTextLinkedHistogram noUnderline" title="4.5 out of 5 stars">
                        <span class="a-icon-alt">4.5 out of 5 stars</span>
                    </span>
                </div>
                <div id="bookDescription_feature_div">
                    <div data-a-expander-name="book_description_expander">
                        <div class="a-expander-content">
                            <p>Test Description</p>
                        </div>
                    </div>
                </div>
            </div>
            <div id="leftCol" class="leftColAlign">
                <div id="booksImageBlock_feature_div">
                    <div id="main-image-container">
                        <img id="landingImage" src="https://example.com/cover.jpg" data-old-hires="https://example.com/cover_high_res.jpg" />
                    </div>
                </div>
            </div>
        </div>
        </html>
        """

        mock_search_response = MagicMock()
        mock_search_response.text = mock_search_html
        mock_search_response.status_code = 200

        mock_detail_response = MagicMock()
        mock_detail_response.text = mock_detail_html
        mock_detail_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[mock_search_response, mock_detail_response]
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.fetch_metadata("9781234567890")

        assert result is not None
        assert result["title"] == "Test Book Title"

    @pytest.mark.asyncio
    async def test_fetch_metadata_not_found(self, provider: AmazonProvider) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>No results</body></html>"
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.fetch_metadata("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_network_error_returns_none(self, provider: AmazonProvider) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.fetch_metadata("9781234567890")

        assert result is None

    @pytest.mark.asyncio
    async def test_rate_limit_error_raises_exception(
        self, provider: AmazonProvider
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with (
            patch.object(provider, "_get_client", return_value=mock_client),
            pytest.raises(Exception, match="Amazon rate limit/unavailable"),
        ):
            await provider.fetch_metadata("any query")

    @pytest.mark.asyncio
    async def test_generic_http_error_returns_none(
        self, provider: AmazonProvider
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.fetch_metadata("any query")

        assert result is None
