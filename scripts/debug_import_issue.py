"""
Debug Import Issue - Systematic Analysis

This script identifies import mismatches between actual class names
and the names used in import statements across the codebase.

Usage:
    python scripts/debug_import_issue.py
    python -m scripts.debug_import_issue
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
import re

# Add project root to sys.path so imports work correctly
# This allows the script to import from src/ regardless of how it's run
HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def extract_class_definitions(file_path: Path) -> Dict[str, str]:
    """
    Extract all class definitions from a Python file.

    Returns:
        Dict mapping class names to their line numbers
    """
    classes = {}

    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes[node.name] = node.lineno

    except Exception as e:
        print(f"[WARNING] Error parsing {file_path}: {e}")

    return classes


def extract_imports(file_path: Path) -> List[Tuple[str, str, int, str]]:
    """
    Extract all imports from a Python file.

    Returns:
        List of tuples: (module, name, line_number, import_type)
        import_type is either 'from' or 'direct'
    """
    imports = []

    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # from X import Y
                if node.module:
                    for alias in node.names:
                        imports.append((
                            node.module,
                            alias.name,
                            node.lineno,
                            'from'
                        ))

            elif isinstance(node, ast.Import):
                # import X
                for alias in node.names:
                    imports.append((
                        alias.name,
                        alias.name.split('.')[-1],
                        node.lineno,
                        'direct'
                    ))

    except Exception as e:
        print(f"[WARNING] Error parsing imports in {file_path}: {e}")

    return imports


def analyze_wisconsin_imports():
    """Analyze Wisconsin WIAA import issues specifically."""

    print("=" * 80)
    print("WISCONSIN WIAA IMPORT ISSUE ANALYSIS")
    print("=" * 80)
    print()

    # 1. Check the actual class definition
    wiaa_source = Path("src/datasources/us/wisconsin_wiaa.py")

    if not wiaa_source.exists():
        print(f"[ERROR] Source file not found: {wiaa_source}")
        return

    print(f"[INFO] Analyzing source file: {wiaa_source}")
    print()

    classes = extract_class_definitions(wiaa_source)

    print("[OK] ACTUAL CLASS DEFINITIONS:")
    for class_name, line_no in classes.items():
        print(f"   Line {line_no:4d}: class {class_name}")
    print()

    # 2. Check all files importing from wisconsin_wiaa
    print("[SCAN] SCANNING FOR IMPORTS...")
    print()

    root = Path(".")
    import_issues = []

    # Scan all Python files
    for py_file in root.rglob("*.py"):
        # Skip venv and other non-project files
        if '.venv' in str(py_file) or '__pycache__' in str(py_file):
            continue

        imports = extract_imports(py_file)

        for module, name, line_no, import_type in imports:
            # Check if this is importing from wisconsin_wiaa
            if 'wisconsin_wiaa' in module:
                # Check if the imported name exists in the actual file
                if name not in classes and name != '*':
                    import_issues.append({
                        'file': py_file,
                        'line': line_no,
                        'module': module,
                        'imported_name': name,
                        'import_type': import_type
                    })

    # 3. Report issues
    if import_issues:
        print("[ERROR] IMPORT ISSUES FOUND:")
        print()

        for issue in import_issues:
            print(f"   [ISSUE] {issue['file']}:{issue['line']}")
            print(f"      Trying to import: {issue['imported_name']}")
            print(f"      From: {issue['module']}")
            print(f"      Type: {issue['import_type']}")

            # Suggest fix
            possible_matches = []
            for actual_class in classes.keys():
                # Case-insensitive match
                if actual_class.lower() == issue['imported_name'].lower():
                    possible_matches.append(actual_class)

            if possible_matches:
                print(f"      [FIX] Suggested fix: Use '{possible_matches[0]}' instead")
            print()

    else:
        print("[OK] No import issues found!")
        print()

    # 4. Check for duplicate imports in same file
    print("[SCAN] CHECKING FOR DUPLICATE IMPORTS...")
    print()

    for py_file in [Path("tests/conftest.py")]:
        if not py_file.exists():
            continue

        imports = extract_imports(py_file)

        # Group by module
        from_wisconsin = [imp for imp in imports if 'wisconsin_wiaa' in imp[0]]

        if len(from_wisconsin) > 1:
            print(f"[WARNING] Multiple imports from wisconsin_wiaa in {py_file}:")
            for module, name, line_no, imp_type in from_wisconsin:
                print(f"   Line {line_no:4d}: from {module} import {name}")
            print()

    return import_issues, classes


def check_venv_installation():
    """Check if package is properly installed in venv."""

    print("=" * 80)
    print("VIRTUAL ENVIRONMENT CHECK")
    print("=" * 80)
    print()

    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print()

    # Check if we can import the package
    try:
        import src.datasources.us.wisconsin_wiaa as wiaa_module
        print("[OK] Package import successful")
        print()

        # List available classes/attributes
        print("Available in wisconsin_wiaa module:")
        attrs = [attr for attr in dir(wiaa_module) if not attr.startswith('_')]
        for attr in sorted(attrs):
            obj = getattr(wiaa_module, attr)
            if isinstance(obj, type):  # It's a class
                print(f"   [CLASS] {attr}")
            else:
                print(f"   [OTHER] {attr} ({type(obj).__name__})")
        print()

    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        print()


def main():
    """Main diagnostic entry point."""

    print()
    print("=" * 80)
    print("SYSTEMATIC IMPORT DIAGNOSTIC TOOL")
    print("Analyzing Wisconsin WIAA DataSource Import Issues")
    print("=" * 80)
    print()

    # Step 1: Check venv
    check_venv_installation()

    # Step 2: Analyze imports
    issues, actual_classes = analyze_wisconsin_imports()

    # Step 3: Summary
    print("=" * 80)
    print("SUMMARY & RECOMMENDED FIXES")
    print("=" * 80)
    print()

    if issues:
        print(f"[ERROR] Found {len(issues)} import issue(s)")
        print()
        print("[FIX] FIXES REQUIRED:")
        print()

        for issue in issues:
            print(f"1. Edit: {issue['file']}")
            print(f"   Line {issue['line']}: Change '{issue['imported_name']}' to correct class name")

            # Find best match
            for actual in actual_classes:
                if actual.lower() == issue['imported_name'].lower():
                    print(f"   Replace: from {issue['module']} import {issue['imported_name']}")
                    print(f"   With:    from {issue['module']} import {actual}")
            print()

    else:
        print("[OK] All imports are correct!")
        print()

    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
