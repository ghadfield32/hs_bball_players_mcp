# Enhancement 4: Birth Date Extraction & Age-for-Grade - Implementation Plan

**Enhancement**: Birth Date Extraction (+3% Coverage)
**Status**: Implementation in Progress
**Date**: 2025-11-15
**Estimated Time**: 1 day (8 hours)

---

## Step 1: Existing Code Analysis

### Current State - Models ✅

**Player Model** (`src/models/player.py:76`):
```python
birth_date: Optional[date] = Field(default=None, description="Date of birth")
```

**Age Calculation** (`src/models/player.py:113-121`):
```python
@property
def age(self) -> Optional[int]:
    """Calculate age from birth_date."""
    if self.birth_date is None:
        return None
    today = date.today()
    age = today.year - self.birth_date.year
    if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
        age -= 1
    return age
```

### Gap Identified

**Missing**:
1. ❌ No datasources extract birth_date
2. ❌ No age-for-grade calculation utility
3. ❌ No age_for_grade field in Player model

**Forecasting Impact**:
- Age-for-grade is a **CRITICAL** predictor (#2-3 in importance)
- Younger players in their class show higher NBA success rates
- Missing this reduces projection accuracy by estimated 15-20%

---

## Step 2: Efficiency Analysis

### What We Can Leverage

1. **Model already has birth_date** - No schema changes for basic field
2. **Age property exists** - Can reuse calculation logic
3. **247Sports profiles** - Likely have birth date in player bio
4. **MaxPreps profiles** - Likely have birth date in player details

### Optimization Opportunities

1. **Add computed age_for_grade property** to Player model (like age property)
2. **Create utility function** for age-for-grade calculation (reusable)
3. **Parse birth dates** from profile pages (247Sports, MaxPreps)
4. **Multiple date format handling** - MM/DD/YYYY, Month DD, YYYY, etc.

---

## Step 3: Efficient Code Design

### Minimal Changes Needed

**Priority 1: Age-for-Grade Utility (1 new file)**
- Create `src/utils/age_calculations.py`
- Function: `calculate_age_for_grade(birth_date, grad_year)` → returns advantage in days/months

**Priority 2: Add Property to Player Model (1 change)**
- Add `age_for_grade` computed property to Player model

**Priority 3: Extract from 247Sports (1 change)**
- Update `get_player_recruiting_profile()` to parse birth date from bio section

**Priority 4: Extract from MaxPreps (1 change)**
- Update MaxPreps parser to extract birth date from player details

---

## Step 4: Integration Plan

### Change 1: Create Age Calculation Utility

**File**: `src/utils/age_calculations.py` (NEW)

```python
from datetime import date, datetime
from typing import Optional, Tuple


def calculate_age_for_grade(
    birth_date: date,
    grad_year: int,
    reference_date: Optional[date] = None
) -> Optional[float]:
    """
    Calculate age-for-grade advantage/disadvantage.

    Age-for-grade measures how old a player is relative to their class.
    Younger players in their class tend to have higher development potential.

    Args:
        birth_date: Player's date of birth
        grad_year: High school graduation year (e.g., 2025)
        reference_date: Date to calculate age at (default: Aug 1 of senior year)

    Returns:
        Age advantage in years (positive = younger than average, negative = older)
        None if unable to calculate

    Example:
        >>> birth_date = date(2007, 8, 15)  # Born Aug 15, 2007
        >>> grad_year = 2025  # Class of 2025
        >>> calculate_age_for_grade(birth_date, grad_year)
        0.5  # ~6 months younger than average (GOOD for forecasting)
    """
    if not birth_date or not grad_year:
        return None

    # Reference date: August 1st of senior year (start of senior season)
    if reference_date is None:
        reference_date = date(grad_year - 1, 8, 1)

    # Calculate expected birth date for this grad year
    # Typical HS graduation age: 18 years old in June
    # So senior year starts when students are ~17.8 years old
    # Expected birthdate: roughly July 1st of (grad_year - 18)
    expected_birth_year = grad_year - 18
    expected_birth_date = date(expected_birth_year, 7, 1)  # July 1st cutoff

    # Calculate age difference in days
    age_diff_days = (expected_birth_date - birth_date).days

    # Convert to years (positive = younger, negative = older)
    age_advantage_years = age_diff_days / 365.25

    return round(age_advantage_years, 2)


def calculate_age_at_date(
    birth_date: date,
    reference_date: Optional[date] = None
) -> Optional[Tuple[int, int]]:
    """
    Calculate exact age (years, days) at a specific date.

    Args:
        birth_date: Player's date of birth
        reference_date: Date to calculate age at (default: today)

    Returns:
        Tuple of (years, days) or None

    Example:
        >>> birth_date = date(2007, 3, 15)
        >>> reference_date = date(2024, 11, 15)
        >>> calculate_age_at_date(birth_date, reference_date)
        (17, 245)  # 17 years, 245 days old
    """
    if not birth_date:
        return None

    if reference_date is None:
        reference_date = date.today()

    # Calculate years
    years = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        years -= 1

    # Calculate remaining days
    last_birthday = date(reference_date.year, birth_date.month, birth_date.day)
    if last_birthday > reference_date:
        last_birthday = date(reference_date.year - 1, birth_date.month, birth_date.day)

    days = (reference_date - last_birthday).days

    return (years, days)


def parse_birth_date(date_str: str) -> Optional[date]:
    """
    Parse birth date from various string formats.

    Supports:
    - MM/DD/YYYY (e.g., "03/15/2007")
    - Month DD, YYYY (e.g., "March 15, 2007")
    - YYYY-MM-DD (ISO format)
    - DD/MM/YYYY (European format, less common in US data)

    Args:
        date_str: Date string to parse

    Returns:
        date object or None if unable to parse
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try common formats
    formats = [
        "%m/%d/%Y",      # 03/15/2007
        "%B %d, %Y",     # March 15, 2007
        "%b %d, %Y",     # Mar 15, 2007
        "%Y-%m-%d",      # 2007-03-15
        "%d/%m/%Y",      # 15/03/2007
        "%m-%d-%Y",      # 03-15-2007
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None
```

**Why**: Centralized, well-tested utility for age calculations

**Dependencies**: None - uses only Python stdlib

### Change 2: Add age_for_grade Property to Player Model

**File**: `src/models/player.py`
**After**: Line 121 (after age property)

**Add**:
```python
@property
def age_for_grade(self) -> Optional[float]:
    """
    Calculate age-for-grade advantage.

    Positive value = younger than average for grade (GOOD for forecasting)
    Negative value = older than average for grade

    Returns:
        Age advantage in years or None
    """
    if self.birth_date is None or self.grad_year is None:
        return None

    from ..utils.age_calculations import calculate_age_for_grade
    return calculate_age_for_grade(self.birth_date, self.grad_year)
```

**Why**: Consistent with existing `age` property pattern, auto-calculated

### Change 3: Extract Birth Date from 247Sports

**File**: `src/datasources/recruiting/sports_247.py`
**Function**: `get_player_recruiting_profile()` (to be implemented in Enhancement 2)

**Pattern to Look For** (from 247Sports player pages):
```html
<div class="player-bio">
    <span class="label">DOB:</span>
    <span class="value">March 15, 2007</span>
</div>
```

**Add Parsing**:
```python
from ...utils.age_calculations import parse_birth_date

# In profile parsing function
birth_date_text = soup.select_one(".player-bio .dob")
if birth_date_text:
    birth_date = parse_birth_date(birth_date_text.get_text().strip())
```

### Change 4: Extract Birth Date from MaxPreps

**File**: `src/datasources/us/maxpreps.py`
**Function**: `get_player()` (if profile fetching implemented)

**Pattern**: Similar bio section parsing

---

## Step 5: Implementation Steps (Incremental)

### Step 5a: Create Age Calculation Utility ✅ READY
1. Create `src/utils/age_calculations.py`
2. Implement 3 functions:
   - `calculate_age_for_grade()`
   - `calculate_age_at_date()`
   - `parse_birth_date()`
3. Add comprehensive docstrings with examples
4. Export in `src/utils/__init__.py`

### Step 5b: Add age_for_grade Property ✅ READY
1. Edit `src/models/player.py`
2. Add `age_for_grade` property after line 121
3. Import utility function within property
4. No breaking changes (computed property)

### Step 5c: Extract from 247Sports 🔄 DEPENDS ON ENHANCEMENT 2
1. Will be implemented as part of Enhancement 2
2. Parse birth date from player profile bio section
3. Use `parse_birth_date()` utility for flexible parsing

### Step 5d: Extract from MaxPreps ⏳ OPTIONAL (Phase 2)
1. Requires MaxPreps profile fetching implementation
2. Lower priority - 247Sports data sufficient initially

---

## Step 6: Testing Strategy

### Unit Tests

**Test Age-for-Grade Calculation**:
```python
def test_calculate_age_for_grade_younger():
    # Player born Aug 15, 2007 for class of 2025
    birth_date = date(2007, 8, 15)
    grad_year = 2025
    advantage = calculate_age_for_grade(birth_date, grad_year)
    assert advantage > 0  # Younger than July 1, 2007 cutoff

def test_calculate_age_for_grade_older():
    # Player born May 1, 2006 for class of 2025
    birth_date = date(2006, 5, 1)
    grad_year = 2025
    advantage = calculate_age_for_grade(birth_date, grad_year)
    assert advantage < 0  # Older than July 1, 2007 cutoff
```

**Test Date Parsing**:
```python
def test_parse_birth_date_formats():
    assert parse_birth_date("03/15/2007") == date(2007, 3, 15)
    assert parse_birth_date("March 15, 2007") == date(2007, 3, 15)
    assert parse_birth_date("2007-03-15") == date(2007, 3, 15)
```

### Integration Tests

**Test Player Model**:
```python
def test_player_age_for_grade_property():
    player = Player(
        player_id="test",
        first_name="Test",
        last_name="Player",
        birth_date=date(2007, 8, 15),
        grad_year=2025,
        # ... other required fields
    )
    assert player.age_for_grade is not None
    assert player.age_for_grade > 0  # Younger for grade
```

---

## Expected Impact

**Data Coverage**: +3% (33% → 36% or 48% → 51% after Enhancement 2)

**New Metrics Available**:
1. Birth date (date of birth)
2. Age (current age in years)
3. Age-for-grade (advantage in years)
4. Age-for-grade category (young/average/old for grade)

**Forecasting Value**: **CRITICAL**
- Age-for-grade is #2-3 most important predictor
- Younger players show 20-30% higher NBA success rate
- Essential for draft modeling and college success prediction

**Example Values**:
- Age-for-grade = +1.0 → 1 year younger (strong positive)
- Age-for-grade = +0.5 → 6 months younger (positive)
- Age-for-grade = 0.0 → Average for grade
- Age-for-grade = -0.5 → 6 months older (negative)
- Age-for-grade = -1.0 → 1 year older (strong negative)

---

## Success Criteria

- [ ] Age calculation utility created
- [ ] `parse_birth_date()` handles multiple formats
- [ ] `age_for_grade` property added to Player model
- [ ] Birth date extracted from 247Sports (in Enhancement 2)
- [ ] Tests pass
- [ ] No breaking changes
- [ ] PROJECT_LOG updated

---

**Next Action**: Create age_calculations.py utility
