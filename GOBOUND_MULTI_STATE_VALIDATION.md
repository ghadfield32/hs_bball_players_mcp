# GoBound Multi-State Validation Report

**Date**: 2025-11-16 07:07:23
**Phase**: HS-2 - Validate GoBound for all 4 Midwest states

---

## Executive Summary

**States Tested**: 4 (IA, IL, MN, SD)
**States Working**: 3 - IA, IL, SD
**States Failed**: 1 - MN

**Player Search Success Rate**: 75%
**Player Stats Success Rate**: 75%

---

## State-by-State Results

### Iowa (IA)

[OK] **Player Search**: SUCCESS - Found 5 players
[OK] **Player Stats**: SUCCESS - 1 stat categories
   - Categories: points

**Data Quality**:
- School Names: [OK]
- Positions: [OK]
- Jersey Numbers: [OK]
- Graduation Years: [OK]

**Sample Players**:
1. Mason Bechen
   - School: North Linn
   - Position: Position.G
   - Jersey: #20
2. Hakeal Powell
   - School: Prince of Peace
   - Position: Position.G
   - Jersey: #1
3. Mason Watkins
   - School: West Burlington
   - Position: Position.G
   - Jersey: #24

**Sample Stats**:
- Points: 779

---

### Illinois (IL)

[OK] **Player Search**: SUCCESS - Found 5 players
[OK] **Player Stats**: SUCCESS - 1 stat categories
   - Categories: points

**Data Quality**:
- School Names: [OK]
- Positions: [OK]
- Jersey Numbers: [OK]
- Graduation Years: [OK]

**Sample Players**:
1. Brady Sehlhorst
   - School: Notre Dame College Prep
   - Position: None
   - Jersey: #4
2. Zackary Sharkey
   - School: Marian Catholic
   - Position: Position.G
   - Jersey: #22
3. Henry Marshall
   - School: Saint Viator
   - Position: Position.G
   - Jersey: #13

**Sample Stats**:
- Points: 158

---

### Minnesota (MN)

[FAIL] **Player Search**: FAILED - Search returned empty list
[FAIL] **Player Stats**: FAILED - None

**Root Cause Analysis**:
- URL exists and loads properly: https://www.gobound.com/mn/mshsl/boysbasketball/2024-25/leaders
- Page structure is correct (tables present)
- **All tables have empty tbody elements** - no player data available
- Tested previous season (2023-24): Also empty
- **Conclusion**: Minnesota does not provide data to GoBound platform

**Data Quality**:
- School Names: [FAIL]
- Positions: [FAIL]
- Jersey Numbers: [FAIL]
- Graduation Years: [FAIL]

---

### South Dakota (SD)

[OK] **Player Search**: SUCCESS - Found 5 players
[OK] **Player Stats**: SUCCESS - 4 stat categories
   - Categories: points, rebounds, steals, blocks

**Data Quality**:
- School Names: [OK]
- Positions: [OK]
- Jersey Numbers: [OK]
- Graduation Years: [OK]

**Sample Players**:
1. Patrick Maynard
   - School: Hitchcock-Tulare
   - Position: Position.F
   - Jersey: #4
2. Devin Enander
   - School: Hitchcock-Tulare
   - Position: Position.G
   - Jersey: #3
3. Rylee Veal
   - School: Bison
   - Position: Position.G
   - Jersey: #15

**Sample Stats**:
- Points: 336
- Rebounds: 142
- Steals: 34
- Blocks: 18

---

## Stat Coverage Comparison

| State | Stat Categories Available |
|-------|---------------------------|
| IA | points |
| IL | points |
| MN | None |
| SD | points, rebounds, steals, blocks |

---

## Conclusion

[WARN] **PARTIAL SUCCESS** - 3/4 states working.
   - Working: IA, IL, SD
   - Failed: MN (no data available on GoBound platform)

**Minnesota Finding**:
   - GoBound lists Minnesota as supported state
   - However, NO player data exists on the platform (checked 2024-25 and 2023-24 seasons)
   - Minnesota may use different statistics platform or not participate in GoBound

**Data Quality**: [WARN] Some inconsistencies detected (position data missing for some IL players)

**Recommendations**:
1. Update documentation to reflect actual coverage: **3 states (IA, IL, SD)** not 4
2. Remove MN from SUPPORTED_STATES or mark as "no data available"
3. Investigate alternative Minnesota sources (SBLive, MaxPreps, local platforms)

**Status**: Phase HS-2 COMPLETE - GoBound validated for 3 Midwest states (75% coverage)
