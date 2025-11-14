"""
Data Source Models

Defines models for tracking data sources and metadata about where data came from.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class DataSourceType(str, Enum):
    """Type of data source."""

    # US - National Circuits
    EYBL = "eybl"  # Nike EYBL (Boys)
    EYBL_GIRLS = "eybl_girls"  # Nike Girls EYBL
    THREE_SSB = "three_ssb"  # Adidas 3 Stripe Select Basketball (Boys)
    THREE_SSB_GIRLS = "three_ssb_girls"  # Adidas 3 Stripe Select Basketball (Girls)
    UAA = "uaa"  # Under Armour Association (Boys)
    UAA_GIRLS = "uaa_girls"  # Under Armour Association (Girls) / UA Next
    GRIND_SESSION = "grind_session"  # Grind Session
    OTE = "ote"  # Overtime Elite

    # US - Multi-State Coverage
    SBLIVE = "sblive"  # SBLive Sports (Multi-state: WA, OR, CA, AZ, ID, NV)
    BOUND = "bound"  # Bound (formerly Varsity Bound) (Multi-state: IA, SD, IL, MN)
    RANKONE = "rankone"  # RankOne Sport (Multi-state: TX, KY, IN, OH, TN - schedules/fixtures)
    MAXPREPS = "maxpreps"  # MaxPreps (All 50 states - UNIVERSAL COVERAGE)

    # US - Recruiting Services
    SPORTS_247 = "247sports"  # 247Sports recruiting rankings, offers, predictions
    ESPN_RECRUITING = "espn_recruiting"  # ESPN recruiting rankings
    RIVALS = "rivals"  # Rivals recruiting (now part of On3)
    ON3 = "on3"  # On3 recruiting and rankings

    # US - Single State
    PSAL = "psal"  # NYC PSAL
    MN_HUB = "mn_hub"  # Minnesota Basketball Hub
    WSN = "wsn"  # Wisconsin Sports Network

    # US - State Associations (Southeast)
    FHSAA = "fhsaa"  # Florida High School Athletic Association
    GHSA = "ghsa"  # Georgia High School Association
    NCHSAA = "nchsaa"  # North Carolina High School Athletic Association
    VHSL = "vhsl"  # Virginia High School League
    TSSAA = "tssaa"  # Tennessee Secondary School Athletic Association
    SCHSL = "schsl"  # South Carolina High School League
    AHSAA = "ahsaa"  # Alabama High School Athletic Association
    LHSAA = "lhsaa"  # Louisiana High School Athletic Association
    MHSAA_MS = "mhsaa_ms"  # Mississippi High School Activities Association
    AAA_AR = "aaa_ar"  # Arkansas Activities Association
    KHSAA = "khsaa"  # Kentucky High School Athletic Association
    WVSSAC = "wvssac"  # West Virginia Secondary School Activities Commission

    # US - State Associations (Northeast)
    CIAC = "ciac"  # Connecticut Interscholastic Athletic Conference
    DIAA = "diaa"  # Delaware Interscholastic Athletic Association
    MIAA = "miaa"  # Massachusetts Interscholastic Athletic Association
    MPSSAA = "mpssaa"  # Maryland Public Secondary Schools Athletic Association
    MPA = "mpa"  # Maine Principals' Association
    NHIAA = "nhiaa"  # New Hampshire Interscholastic Athletic Association
    NJSIAA = "njsiaa"  # New Jersey State Interscholastic Athletic Association
    PIAA = "piaa"  # Pennsylvania Interscholastic Athletic Association
    RIIL = "riil"  # Rhode Island Interscholastic League
    VPA = "vpa"  # Vermont Principals' Association
    NEPSAC = "nepsac"  # New England Preparatory School Athletic Council (Multi-state: CT, MA, ME, NH, RI, VT)

    # US - State Associations (Midwest)
    IHSAA = "ihsaa"  # Indiana High School Athletic Association
    OHSAA = "ohsaa"  # Ohio High School Athletic Association
    KSHSAA = "kshsaa"  # Kansas State High School Activities Association
    MHSAA_MI = "mhsaa_mi"  # Michigan High School Athletic Association
    MSHSAA = "mshsaa"  # Missouri State High School Activities Association
    NDHSAA = "ndhsaa"  # North Dakota High School Activities Association
    NSAA = "nsaa"  # Nebraska School Activities Association

    # US - State Associations (Southwest/West)
    CHSAA = "chsaa"  # Colorado High School Activities Association
    NMAA = "nmaa"  # New Mexico Activities Association
    OSSAA = "ossaa"  # Oklahoma Secondary School Activities Association
    UHSAA = "uhsaa"  # Utah High School Activities Association
    ASAA = "asaa"  # Alaska School Activities Association
    MHSA = "mhsa"  # Montana High School Association
    WHSAA = "whsaa"  # Wyoming High School Activities Association
    DCIAA = "dciaa"  # District of Columbia Interscholastic Athletic Association

    # US - State/Regional Platforms
    HHSAA = "hhsaa"  # Hawaii High School Athletic Association
    TEXAS_HOOPS = "texas_hoops"  # TexasHoops.com
    OIA = "oia"  # Oahu Interscholastic Association (Hawaii)

    # International - Europe
    FIBA = "fiba"  # FIBA Youth
    FIBA_LIVESTATS = "fiba_livestats"  # FIBA LiveStats v7 (Global tournaments)
    ANGT = "angt"  # Adidas Next Generation Tournament (EuroLeague U18)
    NBBL = "nbbl"  # German NBBL/JBBL (U19/U16)
    FEB = "feb"  # Spanish FEB Junior categories
    MKL = "mkl"  # Lithuanian youth leagues
    LNB_ESPOIRS = "lnb_espoirs"  # French LNB Espoirs (U21)

    # International - Canada
    OSBA = "osba"  # Ontario Scholastic Basketball Association
    NPA = "npa"  # National Preparatory Association (Canada)

    # International - Australia
    PLAYHQ = "playhq"  # PlayHQ Australia

    UNKNOWN = "unknown"  # Unknown/other source


class DataSourceRegion(str, Enum):
    """Geographic region of data source."""

    # US National
    US = "us"

    # US States - Southeast
    US_FL = "us_fl"
    US_GA = "us_ga"
    US_NC = "us_nc"
    US_VA = "us_va"
    US_TN = "us_tn"
    US_SC = "us_sc"
    US_AL = "us_al"
    US_LA = "us_la"
    US_MS = "us_ms"
    US_AR = "us_ar"
    US_KY = "us_ky"
    US_WV = "us_wv"

    # US States - Northeast
    US_CT = "us_ct"
    US_DE = "us_de"
    US_MA = "us_ma"
    US_MD = "us_md"
    US_ME = "us_me"
    US_NH = "us_nh"
    US_NJ = "us_nj"
    US_PA = "us_pa"
    US_RI = "us_ri"
    US_VT = "us_vt"
    US_NY = "us_ny"

    # US States - Midwest
    US_IN = "us_in"
    US_OH = "us_oh"
    US_KS = "us_ks"
    US_MI = "us_mi"
    US_MO = "us_mo"
    US_ND = "us_nd"
    US_NE = "us_ne"
    US_MN = "us_mn"
    US_WI = "us_wi"
    US_IA = "us_ia"
    US_SD = "us_sd"
    US_IL = "us_il"

    # US States - Southwest/West
    US_CO = "us_co"
    US_NM = "us_nm"
    US_OK = "us_ok"
    US_UT = "us_ut"
    US_AK = "us_ak"
    US_MT = "us_mt"
    US_WY = "us_wy"
    US_DC = "us_dc"
    US_TX = "us_tx"
    US_HI = "us_hi"

    # US States - West (already covered in multi-state)
    US_WA = "us_wa"
    US_OR = "us_or"
    US_CA = "us_ca"
    US_AZ = "us_az"
    US_ID = "us_id"
    US_NV = "us_nv"

    # International
    CANADA = "canada"
    CANADA_ON = "canada_on"  # Ontario
    EUROPE = "europe"
    EUROPE_DE = "europe_de"  # Germany
    EUROPE_ES = "europe_es"  # Spain
    EUROPE_FR = "europe_fr"  # France
    EUROPE_LT = "europe_lt"  # Lithuania
    AUSTRALIA = "australia"
    GLOBAL = "global"


class DataQualityFlag(str, Enum):
    """Quality flags for data validation."""

    COMPLETE = "complete"  # All expected data present
    PARTIAL = "partial"  # Some data missing
    SUSPECT = "suspect"  # Data present but questionable
    UNVERIFIED = "unverified"  # Not yet validated
    VERIFIED = "verified"  # Manually verified as correct


class DataSource(BaseModel):
    """
    Metadata about where data came from.

    Tracks the source, retrieval time, and quality flags for all data.
    """

    source_type: DataSourceType = Field(description="Type of data source")
    source_name: str = Field(description="Human-readable source name")
    source_url: Optional[HttpUrl] = Field(default=None, description="Source URL")
    region: DataSourceRegion = Field(description="Geographic region")
    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow, description="When data was retrieved"
    )
    quality_flag: DataQualityFlag = Field(
        default=DataQualityFlag.UNVERIFIED, description="Data quality assessment"
    )
    raw_html_cached: bool = Field(default=False, description="Whether raw HTML is cached")
    cache_key: Optional[str] = Field(default=None, description="Cache key for raw data")
    notes: Optional[str] = Field(default=None, description="Additional notes")

    class Config:
        json_schema_extra = {
            "example": {
                "source_type": "eybl",
                "source_name": "Nike EYBL",
                "source_url": "https://nikeeyb.com/stats",
                "region": "us",
                "retrieved_at": "2025-11-11T12:00:00Z",
                "quality_flag": "complete",
                "raw_html_cached": True,
                "cache_key": "eybl_stats_20251111",
                "notes": "Full season stats retrieved successfully",
            }
        }


class RateLimitStatus(BaseModel):
    """Current rate limit status for a data source."""

    source_type: DataSourceType = Field(description="Data source type")
    requests_made: int = Field(ge=0, description="Requests made in current window")
    requests_allowed: int = Field(ge=1, description="Requests allowed per window")
    window_reset_at: datetime = Field(description="When rate limit window resets")
    is_limited: bool = Field(description="Whether currently rate limited")

    @property
    def requests_remaining(self) -> int:
        """Calculate remaining requests in current window."""
        return max(0, self.requests_allowed - self.requests_made)

    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage of rate limit."""
        return (self.requests_made / self.requests_allowed) * 100

    class Config:
        json_schema_extra = {
            "example": {
                "source_type": "eybl",
                "requests_made": 15,
                "requests_allowed": 30,
                "window_reset_at": "2025-11-11T12:01:00Z",
                "is_limited": False,
            }
        }
