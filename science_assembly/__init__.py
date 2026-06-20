"""Science Video Assembly MVP draft package.

This package is intentionally isolated from the existing downloader and subtitle
studio code. It is a draft implementation scaffold for GitHub issue #2.

Safety boundary:
- no automatic YouTube downloading for publication;
- no API keys in source files;
- AI produces structured decisions only;
- local code executes tools after validation and review.
"""

__all__ = ["__version__"]

__version__ = "0.1.0-draft"
