#!/usr/bin/env python3
"""
Debug script to diagnose WisconsinWiaaDataSource import issues.

This script checks:
1. What class names exist in wisconsin_wiaa.py
2. What conftest.py is trying to import
3. Git merge state
4. File differences between branches

Usage:
    python scripts/debug_import_issue.py
"""

import ast
import os
import subprocess
import sys
from pathlib import Path


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)


def check_wisconsin_wiaa_class():
    """Check what class is defined in wisconsin_wiaa.py."""
    print_section("1. Checking wisconsin_wiaa.py Class Definition")

    wiaa_file = Path("src/datasources/us/wisconsin_wiaa.py")

    if not wiaa_file.exists():
        print(f"❌ ERROR: {wiaa_file} does not exist!")
        return None

    print(f"✅ File exists: {wiaa_file}")
    print()

    # Parse the file to find class definitions
    try:
        with open(wiaa_file, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(wiaa_file))

        classes_found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Get the line number
                line_num = node.lineno
                print(f"  Line {line_num}: class {node.name}")
                classes_found.append((node.name, line_num))

        print()
        print(f"📊 Found {len(classes_found)} classes")

        # Check for the specific class we need
        wiaa_classes = [name for name, _ in classes_found if 'wiaa' in name.lower()]
        if wiaa_classes:
            print(f"✅ Wisconsin WIAA class(es): {', '.join(wiaa_classes)}")
            return wiaa_classes[0]
        else:
            print("❌ No Wisconsin WIAA class found!")
            return None

    except Exception as e:
        print(f"❌ ERROR parsing file: {e}")
        return None


def check_conftest_imports():
    """Check what conftest.py is trying to import."""
    print_section("2. Checking conftest.py Import Statement")

    conftest_file = Path("tests/conftest.py")

    if not conftest_file.exists():
        print(f"❌ ERROR: {conftest_file} does not exist!")
        return None

    print(f"✅ File exists: {conftest_file}")
    print()

    # Find the import line
    try:
        with open(conftest_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if 'wisconsin_wiaa import' in line.lower():
                    print(f"  Line {line_num}: {line.strip()}")

                    # Extract the class name being imported
                    if 'import' in line:
                        parts = line.split('import')
                        if len(parts) > 1:
                            imported = parts[1].strip()
                            return imported

        print("⚠️  No wisconsin_wiaa import found")
        return None

    except Exception as e:
        print(f"❌ ERROR reading file: {e}")
        return None


def check_git_state():
    """Check git merge state."""
    print_section("3. Checking Git State")

    try:
        # Current branch
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            check=True
        )
        current_branch = result.stdout.strip()
        print(f"Current branch: {current_branch}")

        # Check for merge in progress
        merge_head = Path(".git/MERGE_HEAD")
        if merge_head.exists():
            print("⚠️  MERGE IN PROGRESS")
            with open(merge_head, 'r') as f:
                merge_commit = f.read().strip()
            print(f"   Merging from: {merge_commit[:8]}")
        else:
            print("✅ No merge in progress")

        # Check for staged changes
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True,
            check=True
        )
        staged = result.stdout.strip().split('\n') if result.stdout.strip() else []
        if staged and staged != ['']:
            print(f"⚠️  {len(staged)} staged files")
            for file in staged[:5]:  # Show first 5
                print(f"   - {file}")
            if len(staged) > 5:
                print(f"   ... and {len(staged) - 5} more")
        else:
            print("✅ No staged changes")

        # Check for uncommitted changes
        result = subprocess.run(
            ['git', 'diff', '--name-only'],
            capture_output=True,
            text=True,
            check=True
        )
        modified = result.stdout.strip().split('\n') if result.stdout.strip() else []
        if modified and modified != ['']:
            print(f"⚠️  {len(modified)} uncommitted changes")
        else:
            print("✅ No uncommitted changes")

    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR running git: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")


def check_file_in_branches():
    """Compare conftest.py between branches."""
    print_section("4. Comparing conftest.py Between Branches")

    branches = [
        'main',
        'claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG'
    ]

    for branch in branches:
        try:
            result = subprocess.run(
                ['git', 'show', f'{branch}:tests/conftest.py'],
                capture_output=True,
                text=True,
                check=True
            )

            # Find the wisconsin import line
            for line_num, line in enumerate(result.stdout.split('\n'), 1):
                if 'wisconsin_wiaa import' in line.lower():
                    print(f"\n{branch}:")
                    print(f"  Line {line_num}: {line.strip()}")
                    break

        except subprocess.CalledProcessError:
            print(f"\n❌ Could not read conftest.py from {branch}")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")


def provide_solution(actual_class: str, imported_class: str):
    """Provide solution based on findings."""
    print_section("5. SOLUTION")

    if actual_class and imported_class:
        if actual_class == imported_class:
            print("✅ Class name and import match!")
            print(f"   Both use: {actual_class}")
            print()
            print("The issue might be in the merge state.")
            print("Try running the solution commands below.")
        else:
            print("❌ MISMATCH FOUND!")
            print(f"   Class defined as: {actual_class}")
            print(f"   Trying to import:  {imported_class}")
            print()
            print("The import statement needs to be corrected.")

    print("\n" + "─" * 80)
    print("RECOMMENDED STEPS TO FIX:")
    print("─" * 80)
    print()
    print("1. Abort the current merge (if in progress):")
    print("   git merge --abort")
    print()
    print("2. Ensure you're on main and it's clean:")
    print("   git checkout main")
    print("   git status")
    print()
    print("3. Pull latest from the feature branch:")
    print("   git fetch origin claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG")
    print()
    print("4. Merge the feature branch cleanly:")
    print("   git merge origin/claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG")
    print()
    print("5. Resolve any conflicts (if prompted)")
    print()
    print("6. OR - Switch to the feature branch directly:")
    print("   git checkout claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG")
    print("   git pull origin claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG")
    print()
    print("7. Run tests again:")
    print("   uv run pytest tests/test_datasources/test_wisconsin_wiaa.py -v")
    print()


def main():
    """Run all diagnostic checks."""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║  Wisconsin WIAA Import Issue Debugger                                      ║
║  Diagnoses class name mismatches and merge conflicts                       ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    # Change to repository root if not already there
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)
    print(f"Working directory: {os.getcwd()}")

    # Run all checks
    actual_class = check_wisconsin_wiaa_class()
    imported_class = check_conftest_imports()
    check_git_state()
    check_file_in_branches()

    # Provide solution
    provide_solution(actual_class, imported_class)

    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
