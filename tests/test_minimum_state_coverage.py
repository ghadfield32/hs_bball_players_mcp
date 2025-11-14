"""
Minimum State Coverage CI Smoke Test

Prevents coverage regression by enforcing a minimum threshold of states
with verified real data. This test ratchets up over time as more states are fixed.

Usage:
    pytest tests/test_minimum_state_coverage.py

CI Integration:
    This test runs on every push to main/PR to detect coverage regressions.
    Threshold starts at 1 (Alabama only) and increases as Phase 24 progresses:
    - Phase 23 baseline: 1 state
    - Session 1 target: 6 states
    - Session 2 target: 15 states
    - Session 3 target: 25 states
    - Phase 24 complete: 35 states
    - Phase 25 complete: 50 states
"""

import json
import pytest
from pathlib import Path


# Ratcheting threshold - increase as states are fixed
# Update this value as coverage improves to prevent regression
MINIMUM_OK_REAL_DATA_STATES = 2  # Phase 24 Session 2: AL + TX verified

# Expected total registered states (Phase 22 = 35, Phase 25 = 50)
EXPECTED_TOTAL_STATES = 35


class TestMinimumStateCoverage:
    """
    CI smoke test to prevent state coverage regression.

    This test fails if:
    1. state_adapter_health.json is missing
    2. ok_real_data count drops below MINIMUM_OK_REAL_DATA_STATES
    3. Total state count drops below EXPECTED_TOTAL_STATES
    """

    def test_health_file_exists(self):
        """Verify state_adapter_health.json exists."""
        health_file = Path("state_adapter_health.json")
        assert health_file.exists(), (
            "state_adapter_health.json not found. "
            "Run: .venv/Scripts/python.exe scripts/probe_state_adapter.py --all --year 2024"
        )

    def test_minimum_ok_real_data_states(self):
        """
        Verify minimum number of states with OK_REAL_DATA status.

        This is the primary coverage regression guard. If this test fails,
        it means one or more previously working states are now broken.
        """
        health_file = Path("state_adapter_health.json")

        if not health_file.exists():
            pytest.skip("state_adapter_health.json not found - run probe first")

        data = json.loads(health_file.read_text())
        summary = data.get("summary", {})
        ok_real_data = summary.get("ok_real_data", 0)
        total_states = summary.get("total_states", 0)

        assert ok_real_data >= MINIMUM_OK_REAL_DATA_STATES, (
            f"Coverage regression detected! "
            f"Expected at least {MINIMUM_OK_REAL_DATA_STATES} states with OK_REAL_DATA, "
            f"but found only {ok_real_data}/{total_states}. "
            f"\n\nBroken states: Check state_adapter_health.json for status != 'OK_REAL_DATA'"
        )

    def test_total_state_count(self):
        """
        Verify total number of registered states matches expected.

        Ensures states aren't accidentally removed from the registry.
        """
        health_file = Path("state_adapter_health.json")

        if not health_file.exists():
            pytest.skip("state_adapter_health.json not found - run probe first")

        data = json.loads(health_file.read_text())
        summary = data.get("summary", {})
        total_states = summary.get("total_states", 0)

        assert total_states >= EXPECTED_TOTAL_STATES, (
            f"State registry shrunk! "
            f"Expected {EXPECTED_TOTAL_STATES} states, found only {total_states}. "
            f"Check STATE_REGISTRY for missing states."
        )

    def test_no_error_states(self):
        """
        Warn if states have ERROR status (not a hard failure).

        ERROR status indicates probe itself failed (exception, timeout, etc.)
        which is different from HTTP_404/NO_GAMES (adapter issues).
        """
        health_file = Path("state_adapter_health.json")

        if not health_file.exists():
            pytest.skip("state_adapter_health.json not found - run probe first")

        data = json.loads(health_file.read_text())
        states = data.get("states", [])

        error_states = [
            s for s in states
            if s.get("status") in ["OTHER", "NETWORK_ERROR", "SSL_ERROR"]
        ]

        if error_states:
            error_list = "\n".join([
                f"  - {s['state']}: {s.get('error_msg', 'Unknown error')[:60]}"
                for s in error_states[:5]
            ])
            pytest.warns(
                UserWarning,
                match=f"{len(error_states)} states have ERROR status"
            )
            print(f"\n⚠️  Warning: {len(error_states)} states with errors:\n{error_list}")

    def test_coverage_improvement_trend(self):
        """
        Track coverage improvement trend (informational).

        This test always passes but reports current coverage for visibility.
        """
        health_file = Path("state_adapter_health.json")

        if not health_file.exists():
            pytest.skip("state_adapter_health.json not found - run probe first")

        data = json.loads(health_file.read_text())
        summary = data.get("summary", {})

        ok_real_data = summary.get("ok_real_data", 0)
        no_games = summary.get("no_games", 0)
        http_404 = summary.get("http_404", 0)
        http_403 = summary.get("http_403", 0)
        http_500 = summary.get("http_500", 0)
        ssl_error = summary.get("ssl_error", 0)
        network_error = summary.get("network_error", 0)
        other = summary.get("other", 0)
        total = summary.get("total_states", 0)
        success_rate = summary.get("success_rate", 0.0)

        # Print coverage report
        print("\n" + "="*80)
        print("STATE ADAPTER COVERAGE REPORT")
        print("="*80)
        print(f"  ✅ OK_REAL_DATA:    {ok_real_data}/{total} ({success_rate}%)")
        print(f"  ⚠️  NO_GAMES:        {no_games}")
        print(f"  ❌ HTTP_404:        {http_404}")
        print(f"  ❌ HTTP_403:        {http_403}")
        print(f"  ❌ HTTP_500:        {http_500}")
        print(f"  ❌ SSL_ERROR:       {ssl_error}")
        print(f"  ❌ NETWORK_ERROR:   {network_error}")
        print(f"  ❌ OTHER:           {other}")
        print("="*80)

        # Suggest next threshold bump
        if ok_real_data >= MINIMUM_OK_REAL_DATA_STATES + 5:
            print(f"\n💡 Coverage improved! Consider bumping MINIMUM_OK_REAL_DATA_STATES to {ok_real_data}")

        # Always pass - this is informational only
        assert True


if __name__ == "__main__":
    # Allow running directly for quick feedback
    pytest.main([__file__, "-v"])
