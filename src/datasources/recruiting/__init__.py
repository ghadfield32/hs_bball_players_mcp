"""Recruiting DataSource Adapters.

Adapters for college basketball recruiting services.
These sources provide rankings, offers, and commitment data.

**Available Sources**:
- Sports247DataSource: 247Sports recruiting (ACTIVE)
- CSVRecruitingDataSource: CSV-based recruiting import (ACTIVE - Enhancement 12.3)
- ESPNRecruitingDataSource: ESPN recruiting (STUB - requires ToS review)
- On3RecruitingDataSource: On3/Rivals recruiting (STUB - requires VIP subscription)
- RivalsRecruitingDataSource: Rivals recruiting (STUB - merged with On3)
"""

from .base_recruiting import BaseRecruitingSource
from .csv_recruiting import CSVRecruitingDataSource
from .espn import ESPNRecruitingDataSource
from .on3 import On3RecruitingDataSource
from .rivals import RivalsRecruitingDataSource
from .sports_247 import Sports247DataSource

__all__ = [
    "BaseRecruitingSource",
    "Sports247DataSource",
    # NEW - Enhancement 12.3: CSV recruiting import (legal, no scraping)
    "CSVRecruitingDataSource",
    # NEW - Enhancement 10, Step 4: Recruiting source stubs
    "ESPNRecruitingDataSource",
    "On3RecruitingDataSource",
    "RivalsRecruitingDataSource",
]
