# KoboSync

**KoboSync** is a lightweight service that synchronizes a local eBook collection with Kobo eReaders. It automates file ingestion, enriches content with metadata, and serves books via the Kobo Sync API.

---

## Features

*   **Lightweight**: Minimal resource footprint. It has no UI, no external dependencies, and runs as a single process.
*   **Automatic Ingestion**: Detects and processes new files immediately upon addition to watched directories.
*   **Metadata Enrichment**: Retrieves high-resolution covers, series information, and ISBNs from Amazon and Goodreads.
*   **Automatic Conversion**: Optionally converts `.epub` files to optimized `.kepub.epub` format.

## Getting Started

To get started with KoboSync, please refer to the following guides:

*   **[Deployment](deployment.md)**: Instructions for running KoboSync using Docker Compose or manually.
*   **[Configuration](configuration.md)**: Comprehensive guide to environment variables and settings.
*   **[Device Setup](device_setup.md)**: Step-by-step instructions to configure your Kobo eReader.
*   **[Architecture](architecture.md)**: Technical overview of the system's design and internals.
