"""
Player Identity Resolution Service

Provides stable player UIDs for cross-source matching and deduplication.
Uses deterministic key-based matching with optional fuzzy fallback.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, Optional, Tuple

from ..models import Player
from ..utils.logger import get_logger

logger = get_logger(__name__)


# In-memory cache: (name_normalized, school_normalized, grad_year) -> canonical uid
_identity_cache: Dict[Tuple[str, str, Optional[int]], str] = {}


def _normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    if not name:
        return ""
    # Remove extra whitespace, convert to lowercase
    return " ".join(name.strip().lower().split())


def _normalize_school(school: str) -> str:
    """Normalize school name for matching."""
    if not school:
        return ""
    # Remove common suffixes and normalize
    school = school.strip().lower()
    for suffix in [" high school", " hs", " academy", " prep"]:
        if school.endswith(suffix):
            school = school[: -len(suffix)].strip()
    return school


def make_player_uid(name: str, school: str, grad_year: Optional[int]) -> str:
    """
    Generate a stable, deterministic player UID.

    Args:
        name: Player's full name
        school: School name
        grad_year: Graduation year (optional)

    Returns:
        Canonical player UID string
    """
    name_norm = _normalize_name(name)
    school_norm = _normalize_school(school)
    grad_str = str(grad_year) if grad_year else "unknown"

    # Create deterministic UID
    uid = f"{name_norm}::{school_norm}::{grad_str}".replace(" ", "_")
    return uid


def resolve_player_uid(
    name: str, school: str, grad_year: Optional[int] = None
) -> str:
    """
    Resolve a player to a stable UID, using cache for consistency.

    Args:
        name: Player's full name
        school: School name
        grad_year: Graduation year (optional)

    Returns:
        Canonical player UID string

    Example:
        >>> resolve_player_uid("John Smith", "Lincoln High School", 2025)
        'john_smith::lincoln::2025'
    """
    name_norm = _normalize_name(name)
    school_norm = _normalize_school(school)

    # Check cache first
    cache_key = (name_norm, school_norm, grad_year)
    if cache_key in _identity_cache:
        return _identity_cache[cache_key]

    # Generate new UID
    uid = make_player_uid(name, school, grad_year)

    # Cache it
    _identity_cache[cache_key] = uid

    logger.debug(
        "Resolved player identity",
        name=name,
        school=school,
        grad_year=grad_year,
        uid=uid,
    )

    return uid


def enrich_player_with_uid(player: Player) -> Player:
    """
    Add a stable player_uid field to a Player model.

    Args:
        player: Player model instance

    Returns:
        Player with player_uid field set
    """
    uid = resolve_player_uid(
        player.full_name, player.school_name or "", player.grad_year
    )

    # Use model_copy to add the uid field
    player_dict = player.model_dump()
    player_dict["player_uid"] = uid

    return Player(**player_dict)


def fuzzy_name_match(name1: str, name2: str, threshold: float = 0.90) -> bool:
    """
    Check if two names are similar using fuzzy matching.

    Args:
        name1: First name
        name2: Second name
        threshold: Similarity threshold (0.0 to 1.0)

    Returns:
        True if names are similar enough

    Example:
        >>> fuzzy_name_match("John Smith", "Jon Smith")
        True
        >>> fuzzy_name_match("John Smith", "Jane Doe")
        False
    """
    name1_norm = _normalize_name(name1)
    name2_norm = _normalize_name(name2)

    if not name1_norm or not name2_norm:
        return False

    ratio = SequenceMatcher(None, name1_norm, name2_norm).ratio()
    return ratio >= threshold


def fuzzy_school_match(school1: str, school2: str, threshold: float = 0.85) -> bool:
    """
    Check if two school names are similar using fuzzy matching.

    Args:
        school1: First school name
        school2: Second school name
        threshold: Similarity threshold (0.0 to 1.0)

    Returns:
        True if school names are similar enough
    """
    school1_norm = _normalize_school(school1)
    school2_norm = _normalize_school(school2)

    if not school1_norm or not school2_norm:
        return False

    ratio = SequenceMatcher(None, school1_norm, school2_norm).ratio()
    return ratio >= threshold


def is_same_player(player1: Player, player2: Player, fuzzy: bool = False) -> bool:
    """
    Determine if two Player objects represent the same person.

    Args:
        player1: First player
        player2: Second player
        fuzzy: Use fuzzy matching (slower but more flexible)

    Returns:
        True if players match
    """
    # Exact matching
    uid1 = resolve_player_uid(
        player1.full_name, player1.school_name or "", player1.grad_year
    )
    uid2 = resolve_player_uid(
        player2.full_name, player2.school_name or "", player2.grad_year
    )

    if uid1 == uid2:
        return True

    # Fuzzy matching (if enabled)
    if fuzzy:
        name_match = fuzzy_name_match(player1.full_name, player2.full_name)
        school_match = fuzzy_school_match(
            player1.school_name or "", player2.school_name or ""
        )

        # Both name and school must match for fuzzy match
        if name_match and school_match:
            # If grad years are available, they should match
            if player1.grad_year and player2.grad_year:
                return player1.grad_year == player2.grad_year
            return True

    return False


def deduplicate_players(players: list[Player], fuzzy: bool = False) -> list[Player]:
    """
    Remove duplicate players from a list.

    Args:
        players: List of Player objects
        fuzzy: Use fuzzy matching for deduplication

    Returns:
        Deduplicated list of players

    Note:
        When duplicates are found, the first occurrence is kept.
    """
    if not players:
        return []

    seen_uids = set()
    result = []

    for player in players:
        uid = resolve_player_uid(
            player.full_name, player.school_name or "", player.grad_year
        )

        if uid in seen_uids:
            continue

        # Check for fuzzy duplicates if enabled
        if fuzzy:
            is_duplicate = False
            for existing in result:
                if is_same_player(player, existing, fuzzy=True):
                    is_duplicate = True
                    break
            if is_duplicate:
                continue

        seen_uids.add(uid)
        result.append(player)

    logger.info(
        "Deduplicated players",
        original_count=len(players),
        deduplicated_count=len(result),
        fuzzy=fuzzy,
    )

    return result


def clear_cache() -> None:
    """Clear the identity resolution cache."""
    global _identity_cache
    _identity_cache.clear()
    logger.info("Cleared identity resolution cache")


def get_cache_stats() -> Dict[str, int]:
    """Get statistics about the identity cache."""
    return {"cached_identities": len(_identity_cache)}
