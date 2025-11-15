"""
Unit tests for 247Sports profile parsing functions (Enhancement 2).

Tests the profile parsing helper functions with mock HTML:
- _build_player_profile_url(): URL construction
- _parse_player_bio(): Birth date and bio extraction
- _parse_player_rankings(): Multi-service rankings extraction
- _parse_player_offers(): College offers parsing
- _parse_crystal_ball(): Predictions extraction
- _classify_conference_level(): Conference classification
- _parse_offer_status(): Status text parsing
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bs4 import BeautifulSoup

from src.datasources.recruiting.sports_247 import Sports247DataSource
from src.models import (
    ConferenceLevel,
    DataSource,
    DataSourceType,
    OfferStatus,
    Region,
)


class TestBuildPlayerProfileURL:
    """Test URL building for player profiles."""

    @pytest.fixture
    def datasource(self):
        """Create Sports247DataSource instance."""
        return Sports247DataSource()

    def test_build_url_with_numeric_id_and_name(self, datasource):
        """Test URL building with numeric ID and player name."""
        player_id = "247_12345"
        player_name = "John Doe"

        url = datasource._build_player_profile_url(player_id, player_name)

        assert url is not None
        assert "John-Doe-12345" in url
        assert url.startswith("https://247sports.com/Player/")

    def test_build_url_without_player_name(self, datasource):
        """Test URL building fails without player name for numeric ID."""
        player_id = "247_12345"

        url = datasource._build_player_profile_url(player_id, player_name=None)

        # Should return None (requires player name for numeric IDs)
        assert url is None

    def test_build_url_with_invalid_prefix(self, datasource):
        """Test URL building fails with invalid player_id prefix."""
        player_id = "invalid_12345"
        player_name = "John Doe"

        url = datasource._build_player_profile_url(player_id, player_name)

        assert url is None

    def test_build_url_with_name_based_id(self, datasource):
        """Test URL building with name-based ID (should fail gracefully)."""
        player_id = "247_john_doe"
        player_name = "John Doe"

        url = datasource._build_player_profile_url(player_id, player_name)

        # Should return None (requires numeric ID for reliable URLs)
        assert url is None

    def test_build_url_name_slug_conversion(self, datasource):
        """Test player name is converted to URL slug correctly."""
        player_id = "247_12345"
        player_name = "Cooper Flagg"

        url = datasource._build_player_profile_url(player_id, player_name)

        assert "Cooper-Flagg-12345" in url


class TestParsePlayerBio:
    """Test bio section parsing including birth date extraction."""

    @pytest.fixture
    def datasource(self):
        """Create Sports247DataSource instance."""
        return Sports247DataSource()

    @pytest.fixture
    def sample_bio_html(self):
        """Sample bio section HTML."""
        return """
        <div class="player-bio">
            <div class="bio-item">
                <span class="label">DOB:</span>
                <span class="value">March 15, 2007</span>
            </div>
            <div class="bio-item">
                <span class="label">Height:</span>
                <span class="value">6-9</span>
            </div>
            <div class="bio-item">
                <span class="label">Weight:</span>
                <span class="value">205</span>
            </div>
            <div class="bio-item">
                <span class="label">Position:</span>
                <span class="value">SF</span>
            </div>
        </div>
        """

    def test_parse_bio_extracts_birth_date(self, datasource, sample_bio_html):
        """Test birth date extraction from bio section."""
        soup = BeautifulSoup(sample_bio_html, "html.parser")
        player_id = "247_12345"
        player_name = "Test Player"

        bio_data = datasource._parse_player_bio(soup, player_id, player_name)

        assert "birth_date" in bio_data
        assert bio_data["birth_date"] == date(2007, 3, 15)

    def test_parse_bio_extracts_height(self, datasource, sample_bio_html):
        """Test height extraction from bio section."""
        soup = BeautifulSoup(sample_bio_html, "html.parser")
        player_id = "247_12345"
        player_name = "Test Player"

        bio_data = datasource._parse_player_bio(soup, player_id, player_name)

        assert "height" in bio_data
        assert bio_data["height"] == "6-9"

    def test_parse_bio_extracts_weight(self, datasource, sample_bio_html):
        """Test weight extraction from bio section."""
        soup = BeautifulSoup(sample_bio_html, "html.parser")
        player_id = "247_12345"
        player_name = "Test Player"

        bio_data = datasource._parse_player_bio(soup, player_id, player_name)

        assert "weight" in bio_data
        assert bio_data["weight"] == 205

    def test_parse_bio_no_bio_section(self, datasource):
        """Test parsing when no bio section exists."""
        html = "<div><p>Some other content</p></div>"
        soup = BeautifulSoup(html, "html.parser")

        bio_data = datasource._parse_player_bio(soup, "247_12345", "Test Player")

        # Should return empty dict
        assert bio_data == {}

    def test_parse_bio_alternative_labels(self, datasource):
        """Test parsing with alternative label names (Birthday, Born)."""
        html = """
        <div class="player-vitals">
            <span class="label">Birthday:</span>
            <span class="value">December 21, 2006</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        bio_data = datasource._parse_player_bio(soup, "247_12345", "Test Player")

        assert "birth_date" in bio_data
        assert bio_data["birth_date"] == date(2006, 12, 21)


class TestClassifyConferenceLevel:
    """Test conference level classification."""

    @pytest.fixture
    def datasource(self):
        """Create Sports247DataSource instance."""
        return Sports247DataSource()

    def test_classify_power_6_acc(self, datasource):
        """Test ACC classified as Power 6."""
        level = datasource._classify_conference_level("ACC")
        assert level == ConferenceLevel.POWER_6

    def test_classify_power_6_big_ten(self, datasource):
        """Test Big Ten classified as Power 6."""
        level = datasource._classify_conference_level("Big Ten")
        assert level == ConferenceLevel.POWER_6

    def test_classify_power_6_sec(self, datasource):
        """Test SEC classified as Power 6."""
        level = datasource._classify_conference_level("SEC")
        assert level == ConferenceLevel.POWER_6

    def test_classify_low_major(self, datasource):
        """Test low major conference classification."""
        level = datasource._classify_conference_level("Summit League")
        assert level == ConferenceLevel.LOW_MAJOR

    def test_classify_mid_major_default(self, datasource):
        """Test unknown conference defaults to mid-major."""
        level = datasource._classify_conference_level("Atlantic 10")
        assert level == ConferenceLevel.MID_MAJOR

    def test_classify_none_conference(self, datasource):
        """Test None conference returns None."""
        level = datasource._classify_conference_level(None)
        assert level is None


class TestParseOfferStatus:
    """Test offer status parsing from text."""

    @pytest.fixture
    def datasource(self):
        """Create Sports247DataSource instance."""
        return Sports247DataSource()

    def test_parse_committed_status(self, datasource):
        """Test 'Committed' text parsed correctly."""
        status = datasource._parse_offer_status("Committed")
        assert status == OfferStatus.COMMITTED

    def test_parse_signed_status(self, datasource):
        """Test 'Signed' text parsed as COMMITTED."""
        status = datasource._parse_offer_status("Signed with Duke")
        assert status == OfferStatus.COMMITTED

    def test_parse_visited_status(self, datasource):
        """Test visit status parsing."""
        status = datasource._parse_offer_status("Official Visit")
        assert status == OfferStatus.VISITED

    def test_parse_offered_default(self, datasource):
        """Test default status is OFFERED."""
        status = datasource._parse_offer_status("Offered")
        assert status == OfferStatus.OFFERED

    def test_parse_decommitted_status(self, datasource):
        """Test decommitted status parsing."""
        status = datasource._parse_offer_status("Decommitted from UNC")
        assert status == OfferStatus.DECOMMITTED


class TestParsePlayerOffers:
    """Test college offers table parsing."""

    @pytest.fixture
    def datasource(self):
        """Create Sports247DataSource instance."""
        return Sports247DataSource()

    @pytest.fixture
    def sample_offers_table_html(self):
        """Sample offers table HTML."""
        return """
        <table class="offer-table">
            <thead>
                <tr>
                    <th>School</th>
                    <th>Conference</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Duke University</td>
                    <td>ACC</td>
                    <td>Committed</td>
                </tr>
                <tr>
                    <td>North Carolina</td>
                    <td>ACC</td>
                    <td>Offered</td>
                </tr>
                <tr>
                    <td>Kentucky</td>
                    <td>SEC</td>
                    <td>Offered</td>
                </tr>
            </tbody>
        </table>
        """

    @pytest.fixture
    def data_source(self):
        """Sample DataSource metadata."""
        return DataSource(
            source_type=DataSourceType.SPORTS_247,
            source_name="247Sports",
            region=Region.US,
        )

    def test_parse_offers_table(self, datasource, sample_offers_table_html, data_source):
        """Test parsing standard offers table."""
        soup = BeautifulSoup(sample_offers_table_html, "html.parser")
        player_id = "247_12345"
        player_name = "Test Player"

        offers = datasource._parse_player_offers(
            soup, player_id, player_name, data_source
        )

        assert len(offers) == 3
        assert offers[0].college_name == "Duke University"
        assert offers[0].offer_status == OfferStatus.COMMITTED
        assert offers[0].conference_level == ConferenceLevel.POWER_6

    def test_parse_offers_power_6_classification(
        self, datasource, sample_offers_table_html, data_source
    ):
        """Test Power 6 offers are classified correctly."""
        soup = BeautifulSoup(sample_offers_table_html, "html.parser")

        offers = datasource._parse_player_offers(
            soup, "247_12345", "Test Player", data_source
        )

        power_6_offers = [o for o in offers if o.conference_level == ConferenceLevel.POWER_6]
        assert len(power_6_offers) == 3  # All ACC and SEC

    def test_parse_offers_no_table(self, datasource, data_source):
        """Test parsing when no offers table exists."""
        html = "<div><p>No offers</p></div>"
        soup = BeautifulSoup(html, "html.parser")

        offers = datasource._parse_player_offers(
            soup, "247_12345", "Test Player", data_source
        )

        assert len(offers) == 0


class TestParseCrystalBall:
    """Test Crystal Ball predictions parsing."""

    @pytest.fixture
    def datasource(self):
        """Create Sports247DataSource instance."""
        return Sports247DataSource()

    @pytest.fixture
    def sample_crystal_ball_html(self):
        """Sample Crystal Ball section HTML."""
        return """
        <div class="crystal-ball-section">
            <div class="prediction-item">
                <span class="expert-name">Jerry Meyer</span>
                <span class="school-predicted">Duke University</span>
                <span class="confidence-level">95%</span>
                <span class="prediction-date">Aug 1, 2024</span>
            </div>
            <div class="prediction-item">
                <span class="expert-name">Eric Bossi</span>
                <span class="school-predicted">Duke University</span>
                <span class="confidence-level">90%</span>
                <span class="prediction-date">Aug 5, 2024</span>
            </div>
            <div class="prediction-item">
                <span class="analyst-name">Brian Snow</span>
                <span class="school-predicted">North Carolina</span>
                <span class="confidence-level">70%</span>
                <span class="prediction-date">Jul 28, 2024</span>
            </div>
        </div>
        """

    @pytest.fixture
    def data_source(self):
        """Sample DataSource metadata."""
        return DataSource(
            source_type=DataSourceType.SPORTS_247,
            source_name="247Sports Crystal Ball",
            region=Region.US,
        )

    def test_parse_crystal_ball(
        self, datasource, sample_crystal_ball_html, data_source
    ):
        """Test parsing Crystal Ball predictions."""
        soup = BeautifulSoup(sample_crystal_ball_html, "html.parser")
        player_id = "247_12345"
        player_name = "Test Player"

        predictions = datasource._parse_crystal_ball(
            soup, player_id, player_name, data_source
        )

        assert len(predictions) == 3
        assert predictions[0].predictor == "Jerry Meyer"
        assert predictions[0].college_predicted == "Duke University"

    def test_parse_crystal_ball_confidence_conversion(
        self, datasource, sample_crystal_ball_html, data_source
    ):
        """Test confidence percentage converted to 0.0-1.0 scale."""
        soup = BeautifulSoup(sample_crystal_ball_html, "html.parser")

        predictions = datasource._parse_crystal_ball(
            soup, "247_12345", "Test Player", data_source
        )

        # 95% should convert to 0.95
        assert predictions[0].confidence == 0.95
        # 90% should convert to 0.90
        assert predictions[1].confidence == 0.90

    def test_parse_crystal_ball_no_section(self, datasource, data_source):
        """Test parsing when no Crystal Ball section exists."""
        html = "<div><p>No predictions</p></div>"
        soup = BeautifulSoup(html, "html.parser")

        predictions = datasource._parse_crystal_ball(
            soup, "247_12345", "Test Player", data_source
        )

        assert len(predictions) == 0


class TestDebugLogging:
    """Test that debug logging is present in all parsing functions."""

    @pytest.fixture
    def datasource(self):
        """Create Sports247DataSource instance."""
        return Sports247DataSource()

    def test_build_url_logs_debug_info(self, datasource, caplog):
        """Test URL building logs debug information."""
        import logging
        caplog.set_level(logging.DEBUG)

        datasource._build_player_profile_url("247_12345", "Test Player")

        # Should have debug logs
        assert any("Building 247Sports player profile URL" in record.message for record in caplog.records)

    def test_parse_bio_logs_fields_extracted(self, datasource, caplog):
        """Test bio parsing logs extracted fields."""
        import logging
        caplog.set_level(logging.DEBUG)

        html = """
        <div class="player-bio">
            <span class="label">DOB:</span>
            <span class="value">March 15, 2007</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        datasource._parse_player_bio(soup, "247_12345", "Test Player")

        # Should log bio parsing activity
        assert any("Parsing player bio section" in record.message for record in caplog.records)


class TestGracefulDegradation:
    """Test that parsing functions degrade gracefully with missing data."""

    @pytest.fixture
    def datasource(self):
        """Create Sports247DataSource instance."""
        return Sports247DataSource()

    def test_bio_parsing_missing_birth_date(self, datasource):
        """Test bio parsing when birth date field missing."""
        html = """
        <div class="player-bio">
            <span class="label">Height:</span>
            <span class="value">6-9</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        bio_data = datasource._parse_player_bio(soup, "247_12345", "Test Player")

        # Should return partial data without birth_date
        assert "birth_date" not in bio_data
        assert "height" in bio_data

    def test_offers_parsing_missing_conference(self, datasource):
        """Test offers parsing when conference missing."""
        html = """
        <table class="offer-table">
            <tr>
                <td>Duke University</td>
                <td></td>
                <td>Offered</td>
            </tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")

        data_source = DataSource(
            source_type=DataSourceType.SPORTS_247,
            source_name="247Sports",
            region=Region.US,
        )

        offers = datasource._parse_player_offers(
            soup, "247_12345", "Test Player", data_source
        )

        # Should still parse offer without conference
        assert len(offers) > 0
        assert offers[0].college_conference is None or offers[0].college_conference == ""

    def test_predictions_missing_confidence(self, datasource):
        """Test predictions parsing when confidence missing."""
        html = """
        <div class="crystal-ball-section">
            <div class="prediction-item">
                <span class="expert-name">Test Expert</span>
                <span class="school-predicted">Duke</span>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        data_source = DataSource(
            source_type=DataSourceType.SPORTS_247,
            source_name="247Sports",
            region=Region.US,
        )

        predictions = datasource._parse_crystal_ball(
            soup, "247_12345", "Test Player", data_source
        )

        # Should still parse prediction without confidence
        assert len(predictions) > 0
        assert predictions[0].confidence is None
