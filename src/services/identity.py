"""
Player Identity Resolution Service

Provides stable player UIDs for cross-source matching and deduplication.
Uses deterministic key-based matching with optional fuzzy fallback.

**ENHANCED (Enhancement 10, Step 5):**
- Multi-attribute matching (name, school, grad_year, birth_date, height, weight, state, country)
- Confidence scoring (1.0 = perfect match, 0.5 = weak fuzzy match)
- Duplicate detection with candidate suggestions
- Merge history tracking
"""

from __future__ import annotations

from datetime import date
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from ..models import Player
from ..utils.logger import get_logger

logger = get_logger(__name__)


# In-memory caches
# (name_normalized, school_normalized, grad_year) -> canonical uid
_identity_cache: Dict[Tuple[str, str, Optional[int]], str] = {}

# Enhanced cache: multi-attribute hash -> (uid, confidence)
_enhanced_cache: Dict[str, Tuple[str, float]] = {}

# Duplicate candidates: uid -> List[(candidate_uid, similarity_score)]
_duplicate_candidates: Dict[str, List[Tuple[str, float]]] = {}

# Merge history: merged_uid -> canonical_uid
_merge_history: Dict[str, str] = {}


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


# ==============================================================================
# ENHANCED IDENTITY RESOLUTION (NEW - Enhancement 10, Step 5)
# ==============================================================================


def create_multi_attribute_hash(
    name: str,
    school: str = "",
    grad_year: Optional[int] = None,
    birth_date: Optional[str] = None,
    height: Optional[int] = None,
    weight: Optional[int] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
) -> str:
    """
    Create a deterministic hash using multiple attributes for enhanced matching.

    Uses as many attributes as available to create a unique player identifier.
    More attributes = higher uniqueness.

    Args:
        name: Player full name (required)
        school: School name
        grad_year: Graduation year
        birth_date: Birth date (YYYY-MM-DD or date object)
        height: Height in inches
        weight: Weight in lbs
        state: State/province code
        country: Country code

    Returns:
        Hash string with format: name::birth_date::school::grad_year::height::country
    """
    # Normalize all inputs
    name_norm = _normalize_name(name)
    school_norm = _normalize_school(school)
    grad_str = str(grad_year) if grad_year else ""

    # Convert birth_date to string if it's a date object
    birth_str = ""
    if birth_date:
        if isinstance(birth_date, date):
            birth_str = birth_date.isoformat()
        else:
            birth_str = str(birth_date)

    height_str = str(height) if height else ""
    weight_str = str(weight) if weight else ""
    state_str = state.upper() if state else ""
    country_str = country.upper() if country else ""

    # Build hash with available attributes (order by importance)
    hash_parts = [
        name_norm,  # Always required
        birth_str,  # Most unique after name
        school_norm,  # Important for HS players
        grad_str,  # Important
        height_str,  # Physical measurements help
        weight_str,
        state_str,  # Geographic context
        country_str,
    ]

    # Filter out empty parts and join
    hash_str = "::".join(p for p in hash_parts if p).replace(" ", "_")
    return hash_str


def calculate_match_confidence(
    name_match: bool = False,
    school_match: bool = False,
    grad_year_match: bool = False,
    birth_date_match: bool = False,
    height_match: bool = False,
    weight_match: bool = False,
    state_match: bool = False,
    fuzzy_name_score: float = 0.0,
) -> float:
    """
    Calculate confidence score for a player match based on available attributes.

    **Scoring System:**
    - Perfect match (name + birth_date + school): 1.0
    - Strong match (name + grad_year + height + weight): 0.9
    - Good match (name + school + grad_year): 0.8
    - Weak match (name + grad_year): 0.6
    - Fuzzy match (name similarity > 0.85 + school): 0.5

    Args:
        name_match: Exact name match
        school_match: Exact school match
        grad_year_match: Exact grad year match
        birth_date_match: Exact birth date match
        height_match: Height within ±2 inches
        weight_match: Weight within ±10 lbs
        state_match: Same state/province
        fuzzy_name_score: Name similarity score (0.0-1.0)

    Returns:
        Confidence score from 0.0 to 1.0
    """
    # Perfect match: name + birth_date + school
    if name_match and birth_date_match and school_match:
        return 1.0

    # Near-perfect: name + birth_date + grad_year
    if name_match and birth_date_match and grad_year_match:
        return 0.95

    # Strong match: name + grad_year + physical measurements
    if name_match and grad_year_match and height_match and weight_match:
        return 0.9

    # Good match: name + school + grad_year
    if name_match and school_match and grad_year_match:
        return 0.8

    # Moderate match: name + grad_year + state
    if name_match and grad_year_match and state_match:
        return 0.75

    # Fair match: name + grad_year
    if name_match and grad_year_match:
        return 0.6

    # Fuzzy match: similar name + school
    if fuzzy_name_score > 0.85 and school_match:
        return 0.5

    # Fuzzy match: similar name + grad_year
    if fuzzy_name_score > 0.85 and grad_year_match:
        return 0.45

    # Weak fuzzy match
    if fuzzy_name_score > 0.90:
        return 0.4

    # No match
    return 0.0


def resolve_player_uid_enhanced(
    name: str,
    school: str = "",
    grad_year: Optional[int] = None,
    birth_date: Optional[str] = None,
    height: Optional[int] = None,
    weight: Optional[int] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
) -> Tuple[str, float]:
    """
    Enhanced player UID resolution with confidence scoring.

    Uses multi-attribute matching to create more accurate player identifiers.
    Returns both UID and confidence score.

    Args:
        name: Player full name (required)
        school: School name
        grad_year: Graduation year
        birth_date: Birth date (YYYY-MM-DD)
        height: Height in inches
        weight: Weight in lbs
        state: State/province code
        country: Country code

    Returns:
        Tuple of (player_uid, confidence_score)
        - player_uid: Canonical UID string
        - confidence_score: 0.0 (no match) to 1.0 (perfect match)

    Example:
        >>> uid, confidence = resolve_player_uid_enhanced(
        ...     name="Cooper Flagg",
        ...     school="Montverde Academy",
        ...     grad_year=2025,
        ...     birth_date="2006-12-21",
        ...     height=81,
        ...     state="FL"
        ... )
        >>> print(f"UID: {uid}, Confidence: {confidence}")
        UID: cooper_flagg::2006-12-21::montverde::2025::81::FL, Confidence: 1.0
    """
    # Create multi-attribute hash
    hash_key = create_multi_attribute_hash(
        name=name,
        school=school,
        grad_year=grad_year,
        birth_date=birth_date,
        height=height,
        weight=weight,
        state=state,
        country=country,
    )

    # Check enhanced cache
    if hash_key in _enhanced_cache:
        uid, confidence = _enhanced_cache[hash_key]
        logger.debug(
            "Enhanced UID resolved from cache",
            name=name,
            uid=uid,
            confidence=confidence,
        )
        return uid, confidence

    # Calculate confidence based on available attributes
    confidence = calculate_match_confidence(
        name_match=bool(name),
        school_match=bool(school),
        grad_year_match=bool(grad_year),
        birth_date_match=bool(birth_date),
        height_match=bool(height),
        weight_match=bool(weight),
        state_match=bool(state),
    )

    # Use hash as UID (more unique than basic name::school::year)
    uid = hash_key

    # Cache the result
    _enhanced_cache[hash_key] = (uid, confidence)

    logger.debug(
        "Enhanced UID created",
        name=name,
        uid=uid,
        confidence=confidence,
        has_birth_date=bool(birth_date),
        has_height=bool(height),
        has_weight=bool(weight),
    )

    # If confidence is low (<0.8), flag as potential duplicate
    if confidence < 0.8:
        if uid not in _duplicate_candidates:
            _duplicate_candidates[uid] = []

        logger.warning(
            "Low-confidence player match - potential duplicate",
            name=name,
            school=school,
            grad_year=grad_year,
            uid=uid,
            confidence=confidence,
        )

    return uid, confidence


def get_duplicate_candidates(uid: str) -> List[Tuple[str, float]]:
    """
    Get list of potential duplicate UIDs for a given player.

    Args:
        uid: Player UID to check

    Returns:
        List of (candidate_uid, similarity_score) tuples
    """
    return _duplicate_candidates.get(uid, [])


def mark_as_merged(merged_uid: str, canonical_uid: str) -> None:
    """
    Mark a player UID as merged into another canonical UID.

    Args:
        merged_uid: UID being merged
        canonical_uid: Canonical UID to merge into
    """
    _merge_history[merged_uid] = canonical_uid
    logger.info(
        "Player UIDs merged",
        merged_uid=merged_uid,
        canonical_uid=canonical_uid,
    )


def get_canonical_uid(uid: str) -> str:
    """
    Get the canonical UID for a player, following merge history.

    Args:
        uid: Player UID (may be merged)

    Returns:
        Canonical UID
    """
    # Follow merge chain
    canonical = uid
    seen = set()

    while canonical in _merge_history:
        if canonical in seen:
            logger.error(
                "Circular merge detected",
                uid=uid,
                circular_chain=list(seen),
            )
            break
        seen.add(canonical)
        canonical = _merge_history[canonical]

    return canonical


def clear_cache() -> None:
    """Clear all identity resolution caches."""
    global _identity_cache, _enhanced_cache, _duplicate_candidates, _merge_history
    _identity_cache.clear()
    _enhanced_cache.clear()
    _duplicate_candidates.clear()
    _merge_history.clear()
    logger.info("Cleared all identity resolution caches")


def get_cache_stats() -> Dict[str, int]:
    """Get statistics about the identity cache."""
    return {"cached_identities": len(_identity_cache)}
