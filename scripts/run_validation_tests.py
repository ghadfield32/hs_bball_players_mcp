"""
Categorical Validation Test Runner

Runs categorical validation tests with clear output and summary.
Useful for Phase 13 verification.

Usage:
    python scripts/run_validation_tests.py [--quick] [--verbose]
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_tests(quick: bool = False, verbose: bool = False) -> int:
    """
    Run categorical validation tests.

    Args:
        quick: Run only quick tests (skip slow tests)
        verbose: Show verbose output

    Returns:
        Exit code (0 = success, non-zero = failure)
    """
    print("=" * 70)
    print("CATEGORICAL VALIDATION TESTS")
    print("=" * 70)
    print()

    # Build pytest command
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/test_unified/test_categorical_validation.py",
    ]

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-v")  # Always verbose for clarity

    if quick:
        cmd.extend(["-m", "not slow"])

    # Add color and summary
    cmd.extend(["--color=yes", "-ra"])

    print("Running command:")
    print("  " + " ".join(cmd))
    print()
    print("-" * 70)
    print()

    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        exit_code = result.returncode

        print()
        print("=" * 70)
        if exit_code == 0:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        print("=" * 70)
        print()

        return exit_code

    except FileNotFoundError:
        print()
        print("=" * 70)
        print("❌ ERROR: pytest not found")
        print("=" * 70)
        print()
        print("Please install dependencies first:")
        print("  pip install -r requirements.txt")
        print()
        print("Or run dependency verification:")
        print("  python scripts/verify_dependencies.py")
        print()
        return 1

    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ ERROR: {e}")
        print("=" * 70)
        print()
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run categorical validation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test categories:
  - CircuitKeysCoverage (3 tests)
  - SourceTypesCoverage (3 tests)
  - GenderNormalization (4 tests)
  - LevelNormalization (5 tests)
  - SourceMetaMapping (4 tests)
  - Phase10And11SourcesCoverage (4 tests)
  - ComprehensiveCoverage (2 tests)

Total: 25 tests

Examples:
  # Run all tests with verbose output:
  python scripts/run_validation_tests.py

  # Run quick tests only:
  python scripts/run_validation_tests.py --quick

  # Extra verbose output:
  python scripts/run_validation_tests.py --verbose
        """,
    )

    parser.add_argument("--quick", action="store_true", help="Run only quick tests")

    parser.add_argument("--verbose", action="store_true", help="Show verbose output")

    args = parser.parse_args()

    return run_tests(quick=args.quick, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
