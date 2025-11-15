"""
State-Specific Basketball DataSources

Directory for state-specific basketball statistics adapters.

Enhancement 12.5: State Datasource Infrastructure

**Purpose**: Add state-specific sources based on coverage gaps from dashboard

**When to Add a State Source**:
1. Run: `python scripts/dashboard_state_coverage.py`
2. Identify states with HIGH priority (many D1 players, low coverage)
3. Find state's official athletic association or partner stats site
4. Copy `state_template.py` and customize for that state

**High-Priority States** (based on D1 production):
- TX: UIL Texas, TexasHoops.com
- CA: CIF California (regional associations)
- FL: FHSAA Florida
- NY: PSAL, CHSAA, Section/Regional sites
- IL: IHSA Illinois

**Template**: See `state_template.py` for implementation guide

Author: Claude Code
Date: 2025-11-15
"""

# When you add a state datasource, import it here
# Example:
# from .tx_uil import UILTexasDataSource
# from .ca_cif import CIFCaliforniaDataSource

__all__ = [
    # Add state datasources here as they are implemented
    # Example:
    # "UILTexasDataSource",
    # "CIFCaliforniaDataSource",
]
