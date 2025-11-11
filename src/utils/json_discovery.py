"""
JSON Discovery Helper

Utilities for discovering and extracting JSON endpoints from HTML pages.
Enables JSON-first scraping strategy for state association websites.
"""

import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Set

from .logger import get_logger

logger = get_logger(__name__)


# Common JSON endpoint patterns in HTML
JSON_URL_PATTERNS = [
    # Direct JSON URLs in script tags, data attributes, etc.
    r'"(https?://[^"]+\.json[^"]*)"',
    r"'(https?://[^']+\.json[^']*)'",
    # API endpoints
    r'"(https?://[^"]+/api/[^"]+)"',
    r"'(https?://[^']+/api/[^']+)'",
    # Data endpoints
    r'"(https?://[^"]+/data/[^"]+)"',
    r"'(https?://[^']+/data/[^']+)'",
    # Widget/feed endpoints
    r'"(https?://[^"]+/widget/[^"]+)"',
    r"'(https?://[^']+/widget/[^']+)'",
    r'"(https?://[^"]+/feed/[^"]+)"',
    r"'(https?://[^']+/feed/[^']+)'",
]


def discover_json_endpoints(html: str, base_url: str) -> List[str]:
    """
    Discover JSON endpoints embedded in HTML.

    Args:
        html: HTML content to search
        base_url: Base URL for resolving relative URLs

    Returns:
        List of discovered JSON endpoint URLs (deduplicated, ordered by discovery)
    """
    urls: Set[str] = set()
    ordered_urls: List[str] = []

    # Search for JSON URLs using patterns
    for pattern in JSON_URL_PATTERNS:
        for match in re.finditer(pattern, html, flags=re.IGNORECASE):
            url = match.group(1)

            # Normalize URL
            url = _normalize_url(url, base_url)

            # Add if new
            if url and url not in urls:
                urls.add(url)
                ordered_urls.append(url)
                logger.debug(f"Discovered JSON endpoint", url=url)

    logger.info(
        f"Discovered {len(ordered_urls)} JSON endpoints",
        base_url=base_url,
        endpoints=len(ordered_urls),
    )

    return ordered_urls


def extract_inline_json(html: str, var_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract inline JSON data from JavaScript variables in HTML.

    Looks for patterns like:
    - var data = {...};
    - window.data = {...};
    - const data = {...};

    Args:
        html: HTML content containing inline JSON
        var_name: Optional variable name to search for (e.g., 'scheduleData')

    Returns:
        List of extracted JSON objects
    """
    results: List[Dict[str, Any]] = []

    if var_name:
        # Search for specific variable
        patterns = [
            rf"(?:var|let|const)\s+{var_name}\s*=\s*(\{{[^;]+\}});",
            rf"window\.{var_name}\s*=\s*(\{{[^;]+\}});",
        ]
    else:
        # Search for any JSON-like assignment
        patterns = [
            r"(?:var|let|const)\s+\w+\s*=\s*(\{[^;]+\});",
            r"window\.\w+\s*=\s*(\{[^;]+\});",
        ]

    for pattern in patterns:
        for match in re.finditer(pattern, html, flags=re.DOTALL):
            json_str = match.group(1)
            try:
                data = json.loads(json_str)
                results.append(data)
                logger.debug(f"Extracted inline JSON", size=len(json_str))
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse inline JSON", error=str(e))
                continue

    logger.info(f"Extracted {len(results)} inline JSON objects")
    return results


def is_json_response(content_type: str) -> bool:
    """
    Check if content type indicates JSON response.

    Args:
        content_type: HTTP Content-Type header value

    Returns:
        True if JSON content type
    """
    if not content_type:
        return False

    content_type = content_type.lower()
    return (
        "application/json" in content_type
        or "application/javascript" in content_type
        or "text/json" in content_type
    )


def _normalize_url(url: str, base_url: str) -> Optional[str]:
    """
    Normalize and resolve URL.

    Args:
        url: URL to normalize
        base_url: Base URL for resolving relative URLs

    Returns:
        Normalized absolute URL or None if invalid
    """
    if not url:
        return None

    # Remove quotes and whitespace
    url = url.strip().strip("'\"")

    # Skip data URLs, javascript:, etc.
    if url.startswith(("data:", "javascript:", "mailto:", "#")):
        return None

    # Handle protocol-relative URLs
    if url.startswith("//"):
        url = "https:" + url

    # Handle relative URLs
    if not url.startswith(("http://", "https://")):
        url = urllib.parse.urljoin(base_url, url)

    # Validate URL
    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
    except Exception:
        return None

    return url


def filter_json_by_keywords(
    urls: List[str], keywords: List[str], exclude: Optional[List[str]] = None
) -> List[str]:
    """
    Filter JSON URLs by keywords.

    Args:
        urls: List of URLs to filter
        keywords: Keywords that should appear in URL (OR condition)
        exclude: Keywords that should NOT appear in URL (AND condition)

    Returns:
        Filtered list of URLs
    """
    filtered: List[str] = []
    exclude = exclude or []

    for url in urls:
        url_lower = url.lower()

        # Check if any keyword matches
        has_keyword = any(kw.lower() in url_lower for kw in keywords)

        # Check if any exclude keyword matches
        has_exclude = any(ex.lower() in url_lower for ex in exclude)

        if has_keyword and not has_exclude:
            filtered.append(url)

    logger.info(
        f"Filtered JSON URLs by keywords",
        total=len(urls),
        filtered=len(filtered),
        keywords=keywords,
        exclude=exclude,
    )

    return filtered
