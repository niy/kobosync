# Configuration

Kobold is configured via environment variables.

## Core Settings

| Variable | Default | Description |
| :--- | :--- | :--- |
| `KS_USER_TOKEN` | *(none)* | **Required**: Secure token for API authentication. App will fail to start if missing. |
| `KS_DATA_PATH` | `./data` | Directory for persistent application data (`kobold.db`). |
| `KS_WATCH_DIRS` | `/books` | Comma-separated list of directories to monitor. |
| `KS_WORKER_POLL_INTERVAL` | `300.0` | Interval in seconds between worker polls for new jobs (metadata, conversion). |
| `KS_LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

## Metadata Providers

| Variable | Default | Description |
| :--- | :--- | :--- |
| `KS_AMAZON_DOMAIN` | `com` | Amazon region domain (e.g., `com`, `co.uk`, `de`, `jp`). |
| `KS_AMAZON_COOKIE` | *(empty)* | Optional session cookie for authenticated requests to avoid rate limits. |

## Feature Flags

| Variable | Default | Description |
| :--- | :--- | :--- |
| `KS_CONVERT_EPUB` | `True` | Automatically convert `.epub` to `.kepub.epub`. |
| `KS_DELETE_ORIGINAL_AFTER_CONVERSION` | `False` | Delete the original `.epub` file after successful conversion. |
| `KS_EMBED_METADATA` | `False` | Write scraped metadata (cover, author, ISBN) back into the source file. |
| `KS_FETCH_EXTERNAL_METADATA` | `True` | Query external sources (Amazon, Goodreads) for metadata. Set to `False` in test environments to avoid hitting external APIs. |

## File Watcher

| Variable | Default | Description |
| :--- | :--- | :--- |
| `KS_WATCH_FORCE_POLLING` | `False` | Force polling mode. Required for some network shares (NFS/SMB). |
| `KS_WATCH_POLL_DELAY_MS` | `300` | Polling interval in milliseconds (used only if polling is active). |
