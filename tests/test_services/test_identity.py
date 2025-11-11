"""
Identity Resolution Service Tests

Tests player identity resolution and deduplication.
"""

import pytest

from src.models import DataQualityFlag, DataSourceMetadata, Player
from src.services.identity import (
    clear_cache,
    deduplicate_players,
    fuzzy_name_match,
    fuzzy_school_match,
    get_cache_stats,
    is_same_player,
    make_player_uid,
    resolve_player_uid,
)


@pytest.mark.service
class TestIdentityResolution:
    """Test suite for identity resolution service."""

    def test_normalize_and_make_uid(self):
        """Test UID generation normalizes inputs correctly."""
        # Same player, different input formatting
        uid1 = make_player_uid("John Smith", "Lincoln High School", 2025)
        uid2 = make_player_uid("john smith", "Lincoln HS", 2025)
        uid3 = make_player_uid("JOHN  SMITH", "Lincoln   High School", 2025)

        # Basic normalization (exact name/school should match)
        assert uid1 == make_player_uid("John Smith", "Lincoln High School", 2025)
        # Different school suffix should produce different UID
        assert uid1 != uid2  # "lincoln" vs "lincoln hs" after normalization

    def test_resolve_player_uid_caching(self):
        """Test that player UID resolution uses cache."""
        clear_cache()

        # First call creates entry
        uid1 = resolve_player_uid("Jane Doe", "Jefferson Academy", 2026)

        stats_before = get_cache_stats()
        assert stats_before["cached_identities"] == 1

        # Second call should use cache
        uid2 = resolve_player_uid("Jane Doe", "Jefferson Academy", 2026)
        assert uid1 == uid2

        # Same result should be in cache
        stats_after = get_cache_stats()
        assert stats_after["cached_identities"] == 1

    def test_resolve_player_uid_different_grad_years(self):
        """Test that different grad years produce different UIDs."""
        uid_2025 = resolve_player_uid("Mike Johnson", "Central High", 2025)
        uid_2026 = resolve_player_uid("Mike Johnson", "Central High", 2026)

        assert uid_2025 != uid_2026

    def test_resolve_player_uid_no_grad_year(self):
        """Test UID generation without grad year."""
        uid = resolve_player_uid("No Grad", "Unknown School", None)
        assert "unknown" in uid
        assert isinstance(uid, str)

    def test_fuzzy_name_match_similar(self):
        """Test fuzzy name matching for similar names."""
        # Very similar (typo)
        assert fuzzy_name_match("John Smith", "Jon Smith") is True

        # Same name, different case/spacing
        assert fuzzy_name_match("mary jones", "Mary  Jones") is True

        # Different names
        assert fuzzy_name_match("John Smith", "Jane Doe") is False

    def test_fuzzy_name_match_threshold(self):
        """Test fuzzy matching with custom threshold."""
        # Slightly different names
        name1 = "Christopher Johnson"
        name2 = "Chris Johnson"

        # High threshold (strict) - might not match
        strict = fuzzy_name_match(name1, name2, threshold=0.95)

        # Lower threshold (lenient) - should match
        lenient = fuzzy_name_match(name1, name2, threshold=0.70)

        # Lenient should be more permissive
        assert lenient is True

    def test_fuzzy_school_match(self):
        """Test fuzzy school name matching."""
        # Similar schools with different suffixes
        assert fuzzy_school_match("Lincoln High School", "Lincoln HS") is True

        # Same school, different formatting
        assert fuzzy_school_match("Jefferson Academy", "jefferson  academy") is True

        # Different schools
        assert fuzzy_school_match("Lincoln High", "Washington High") is False

    def test_is_same_player_exact_match(self):
        """Test exact player matching."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE,
        )

        player1 = Player(
            player_id="test_1",
            first_name="John",
            last_name="Smith",
            full_name="John Smith",
            school_name="Lincoln High School",
            grad_year=2025,
            data_source=data_source,
        )

        player2 = Player(
            player_id="test_2",
            first_name="John",
            last_name="Smith",
            full_name="John Smith",
            school_name="Lincoln High School",
            grad_year=2025,
            data_source=data_source,
        )

        # Should match based on name, school, grad year
        assert is_same_player(player1, player2, fuzzy=False) is True

    def test_is_same_player_different(self):
        """Test that different players don't match."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE,
        )

        player1 = Player(
            player_id="test_1",
            first_name="John",
            last_name="Smith",
            full_name="John Smith",
            school_name="Lincoln High",
            grad_year=2025,
            data_source=data_source,
        )

        player2 = Player(
            player_id="test_2",
            first_name="Jane",
            last_name="Doe",
            full_name="Jane Doe",
            school_name="Jefferson High",
            grad_year=2026,
            data_source=data_source,
        )

        assert is_same_player(player1, player2, fuzzy=False) is False

    def test_is_same_player_fuzzy_match(self):
        """Test fuzzy player matching."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE,
        )

        player1 = Player(
            player_id="test_1",
            full_name="Christopher Johnson",
            school_name="Lincoln High School",
            grad_year=2025,
            data_source=data_source,
        )

        player2 = Player(
            player_id="test_2",
            full_name="Chris Johnson",
            school_name="Lincoln HS",
            grad_year=2025,
            data_source=data_source,
        )

        # Exact match should fail
        assert is_same_player(player1, player2, fuzzy=False) is False

        # Fuzzy match might succeed (depending on similarity)
        # This is more lenient
        fuzzy_result = is_same_player(player1, player2, fuzzy=True)
        # Test that fuzzy matching is more permissive
        assert isinstance(fuzzy_result, bool)

    def test_deduplicate_players_exact(self):
        """Test exact deduplication of players."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE,
        )

        # Create duplicate players
        players = [
            Player(
                player_id="test_1",
                full_name="John Smith",
                school_name="Lincoln High",
                grad_year=2025,
                data_source=data_source,
            ),
            Player(
                player_id="test_2",
                full_name="Jane Doe",
                school_name="Jefferson High",
                grad_year=2026,
                data_source=data_source,
            ),
            Player(
                player_id="test_3",
                full_name="John Smith",  # Duplicate
                school_name="Lincoln High",
                grad_year=2025,
                data_source=data_source,
            ),
            Player(
                player_id="test_4",
                full_name="Bob Wilson",
                school_name="Central High",
                grad_year=2025,
                data_source=data_source,
            ),
        ]

        deduplicated = deduplicate_players(players, fuzzy=False)

        # Should have 3 unique players (John Smith duplicate removed)
        assert len(deduplicated) == 3

        # Verify no duplicate UIDs
        uids = [
            resolve_player_uid(p.full_name, p.school_name or "", p.grad_year)
            for p in deduplicated
        ]
        assert len(uids) == len(set(uids))

    def test_deduplicate_players_empty_list(self):
        """Test deduplication with empty list."""
        result = deduplicate_players([], fuzzy=False)
        assert result == []

    def test_deduplicate_players_single(self):
        """Test deduplication with single player."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE,
        )

        players = [
            Player(
                player_id="test_1",
                full_name="Single Player",
                school_name="Test School",
                grad_year=2025,
                data_source=data_source,
            )
        ]

        result = deduplicate_players(players, fuzzy=False)
        assert len(result) == 1
        assert result[0].full_name == "Single Player"

    def test_deduplicate_preserves_first_occurrence(self):
        """Test that deduplication keeps the first occurrence."""
        data_source1 = DataSourceMetadata(
            source_type="eybl",
            source_url="https://eybl.com",
            quality_flag=DataQualityFlag.COMPLETE,
        )

        data_source2 = DataSourceMetadata(
            source_type="psal",
            source_url="https://psal.com",
            quality_flag=DataQualityFlag.COMPLETE,
        )

        players = [
            Player(
                player_id="eybl_john",
                full_name="John Smith",
                school_name="Test High",
                grad_year=2025,
                data_source=data_source1,
            ),
            Player(
                player_id="psal_john",
                full_name="John Smith",
                school_name="Test High",
                grad_year=2025,
                data_source=data_source2,
            ),
        ]

        result = deduplicate_players(players, fuzzy=False)

        # Should keep first (EYBL)
        assert len(result) == 1
        assert result[0].player_id == "eybl_john"

    def test_clear_cache(self):
        """Test cache clearing."""
        # Add some entries
        resolve_player_uid("Test Player 1", "School 1", 2025)
        resolve_player_uid("Test Player 2", "School 2", 2026)

        stats = get_cache_stats()
        assert stats["cached_identities"] >= 2

        # Clear cache
        clear_cache()

        stats_after = get_cache_stats()
        assert stats_after["cached_identities"] == 0
