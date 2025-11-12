"""
Dependency Verification Script

Verifies all required dependencies are installed and provides
installation instructions if any are missing.

Usage:
    python scripts/verify_dependencies.py
"""

import importlib
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_dependency(module_name: str, package_name: str = None) -> bool:
    """
    Check if a dependency is installed.

    Args:
        module_name: Name of the module to import
        package_name: Name of the package (if different from module)

    Returns:
        True if installed, False otherwise
    """
    if package_name is None:
        package_name = module_name

    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def main():
    """Main dependency check."""
    print("=" * 60)
    print("DEPENDENCY VERIFICATION")
    print("=" * 60)
    print()

    # Core dependencies
    dependencies = {
        "Core Framework": [
            ("pydantic", "pydantic"),
            ("pydantic_settings", "pydantic-settings"),
            ("fastapi", "fastapi"),
            ("uvicorn", "uvicorn"),
        ],
        "HTTP & Parsing": [
            ("httpx", "httpx"),
            ("bs4", "beautifulsoup4"),
            ("tenacity", "tenacity"),
        ],
        "Data Processing": [
            ("pandas", "pandas"),
            ("numpy", "numpy"),
            ("duckdb", "duckdb"),
            ("pyarrow", "pyarrow"),
        ],
        "Testing": [
            ("pytest", "pytest"),
            ("pytest_asyncio", "pytest-asyncio"),
            ("pytest_cov", "pytest-cov"),
            ("pytest_mock", "pytest-mock"),
        ],
        "Utilities": [
            ("yaml", "pyyaml"),
            ("dotenv", "python-dotenv"),
        ],
    }

    missing = []
    installed = []

    for category, deps in dependencies.items():
        print(f"\n{category}:")
        print("-" * 40)

        for module_name, package_name in deps:
            if check_dependency(module_name, package_name):
                print(f"  ✓ {package_name}")
                installed.append(package_name)
            else:
                print(f"  ✗ {package_name} - MISSING")
                missing.append(package_name)

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Installed: {len(installed)}/{len(installed) + len(missing)}")
    print(f"Missing: {len(missing)}")
    print()

    if missing:
        print("❌ Missing dependencies detected!")
        print()
        print("To install missing dependencies:")
        print()
        print("  pip install -r requirements.txt")
        print()
        print("Or install individually:")
        print()
        for package in missing:
            print(f"  pip install {package}")
        print()
        return 1
    else:
        print("✅ All dependencies installed!")
        print()
        print("You are ready to:")
        print("  1. Run categorical validation tests")
        print("  2. Activate template adapters")
        print("  3. Deploy auto-export system")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
