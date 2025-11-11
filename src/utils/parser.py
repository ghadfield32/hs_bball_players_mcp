"""
HTML Parsing Utilities

Helper functions for parsing HTML and extracting data from web pages.
"""

from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from .logger import get_logger

logger = get_logger(__name__)


def parse_html(html: str, parser: str = "lxml") -> BeautifulSoup:
    """
    Parse HTML string into BeautifulSoup object.

    Args:
        html: HTML string
        parser: Parser to use (lxml, html.parser, html5lib)

    Returns:
        BeautifulSoup object
    """
    return BeautifulSoup(html, parser)


def get_text_or_none(element: Optional[Tag], strip: bool = True) -> Optional[str]:
    """
    Safely get text from element or return None.

    Args:
        element: BeautifulSoup element
        strip: Whether to strip whitespace

    Returns:
        Text content or None
    """
    if element is None:
        return None

    text = element.get_text()
    return text.strip() if strip else text


def get_attr_or_none(element: Optional[Tag], attr: str) -> Optional[str]:
    """
    Safely get attribute from element or return None.

    Args:
        element: BeautifulSoup element
        attr: Attribute name

    Returns:
        Attribute value or None
    """
    if element is None:
        return None

    return element.get(attr)


def parse_int(value: Any) -> Optional[int]:
    """
    Safely parse integer from value.

    Args:
        value: Value to parse

    Returns:
        Parsed integer or None
    """
    if value is None:
        return None

    try:
        # Remove common formatting (commas, spaces)
        if isinstance(value, str):
            value = value.replace(",", "").replace(" ", "").strip()

        return int(value)
    except (ValueError, TypeError):
        return None


def parse_float(value: Any) -> Optional[float]:
    """
    Safely parse float from value.

    Args:
        value: Value to parse

    Returns:
        Parsed float or None
    """
    if value is None:
        return None

    try:
        # Remove common formatting
        if isinstance(value, str):
            value = value.replace(",", "").replace(" ", "").strip()
            # Handle percentages
            if value.endswith("%"):
                value = value[:-1]

        return float(value)
    except (ValueError, TypeError):
        return None


def parse_stat(text: str) -> tuple[Optional[int], Optional[int]]:
    """
    Parse stat in format "made/attempted" or "made-attempted".

    Args:
        text: Stat text (e.g., "5/10", "5-10")

    Returns:
        Tuple of (made, attempted) or (None, None)
    """
    if not text:
        return None, None

    try:
        # Clean text
        text = text.strip()

        # Try different separators
        if "/" in text:
            parts = text.split("/")
        elif "-" in text:
            parts = text.split("-")
        else:
            return None, None

        if len(parts) != 2:
            return None, None

        made = parse_int(parts[0])
        attempted = parse_int(parts[1])

        return made, attempted

    except Exception:
        return None, None


def parse_height_to_inches(height: str) -> Optional[int]:
    """
    Parse height string to inches.

    Handles formats: "6'2", "6-2", "6'2\"", "6-2\"", "6 2", "74"

    Args:
        height: Height string

    Returns:
        Height in inches or None
    """
    if not height:
        return None

    try:
        # Clean text
        height = height.strip().replace("\"", "")

        # Try formats with feet/inches
        if "'" in height or "-" in height or " " in height:
            # Replace separators with space
            height = height.replace("'", " ").replace("-", " ")
            parts = height.split()

            if len(parts) >= 2:
                feet = parse_int(parts[0])
                inches = parse_int(parts[1])

                if feet is not None and inches is not None:
                    return feet * 12 + inches

        # Try as raw inches
        return parse_int(height)

    except Exception:
        return None


def parse_record(record: str) -> tuple[Optional[int], Optional[int]]:
    """
    Parse win-loss record.

    Args:
        record: Record string (e.g., "12-3", "12W-3L")

    Returns:
        Tuple of (wins, losses) or (None, None)
    """
    if not record:
        return None, None

    try:
        # Remove W/L indicators
        record = record.upper().replace("W", "").replace("L", "").strip()

        # Parse as stat
        return parse_stat(record)

    except Exception:
        return None, None


def clean_player_name(name: str) -> str:
    """
    Clean player name by removing numbers, special characters.

    Args:
        name: Raw player name

    Returns:
        Cleaned name
    """
    if not name:
        return ""

    # Remove leading numbers (jersey numbers)
    name = name.strip()

    # Remove common prefixes
    for prefix in ["#", "No.", "No"]:
        if name.startswith(prefix):
            name = name[len(prefix) :].strip()

    # Remove any leading digits
    while name and name[0].isdigit():
        name = name[1:].strip()

    return name.strip()


def extract_table_data(table: Tag) -> list[dict[str, str]]:
    """
    Extract data from HTML table into list of dictionaries.

    Args:
        table: BeautifulSoup table element

    Returns:
        List of row dictionaries with column headers as keys
    """
    rows = []

    # Find headers
    headers = []
    thead = table.find("thead")
    if thead:
        header_cells = thead.find_all(["th", "td"])
        headers = [get_text_or_none(cell, strip=True) or f"col_{i}" for i, cell in enumerate(header_cells)]
    else:
        # Try first row as headers
        first_row = table.find("tr")
        if first_row:
            header_cells = first_row.find_all(["th", "td"])
            if any(cell.name == "th" for cell in header_cells):
                headers = [get_text_or_none(cell, strip=True) or f"col_{i}" for i, cell in enumerate(header_cells)]

    if not headers:
        # Generic column names
        first_row = table.find("tr")
        if first_row:
            cells = first_row.find_all(["th", "td"])
            headers = [f"col_{i}" for i in range(len(cells))]

    # Extract rows
    tbody = table.find("tbody") or table
    for row in tbody.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if cells:
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row_data[headers[i]] = get_text_or_none(cell, strip=True)
            if row_data:  # Only add non-empty rows
                rows.append(row_data)

    return rows
