#!/usr/bin/env python3
"""
Setup verification script for DataPulse SQLite connector.

This script verifies that the package is properly installed
and all components are working correctly.
"""

import importlib
import inspect
import sys
from pathlib import Path


def check_imports():
    """Check if all required modules can be imported."""
    print("🔍 Checking imports...")

    required_modules = [
        "metronome_pulse_sqlite",
        "metronome_pulse_sqlite.connector",
        "metronome_pulse_sqlite.readonly_connector",
        "metronome_pulse_sqlite.writeonly_connector",
    ]

    success = True
    for module_name in required_modules:
        try:
            module = importlib.import_module(module_name)
            print(f"   ✅ {module_name}")
        except ImportError as e:
            print(f"   ❌ {module_name}: {e}")
            success = False

    return success


def check_classes():
    """Check if all required classes are available."""
    print("\n🔍 Checking classes...")

    try:
        from metronome_pulse_sqlite import (
            SQLitePulse,
            SQLiteReadonlyPulse,
            SQLiteWriteonlyPulse,
        )

        classes = [SQLitePulse, SQLiteReadonlyPulse, SQLiteWriteonlyPulse]
        class_names = ["SQLitePulse", "SQLiteReadonlyPulse", "SQLiteWriteonlyPulse"]

        success = True
        for cls, name in zip(classes, class_names):
            if inspect.isclass(cls):
                print(f"   ✅ {name} class found")

                # Check if it has required methods
                required_methods = ["connect", "close", "is_connected"]
                for method in required_methods:
                    if hasattr(cls, method):
                        print(f"      ✅ {method} method found")
                    else:
                        print(f"      ❌ {method} method missing")
                        success = False
            else:
                print(f"   ❌ {name} is not a class")
                success = False

        return success

    except ImportError as e:
        print(f"   ❌ Failed to import classes: {e}")
        return False


def check_package_structure():
    """Check if the package structure is correct."""
    print("\n🔍 Checking package structure...")

    package_dir = Path(__file__).parent / "metronome_pulse_sqlite"

    if not package_dir.exists():
        print(f"   ❌ Package directory not found: {package_dir}")
        return False

    required_files = [
        "__init__.py",
        "connector.py",
        "readonly_connector.py",
        "writeonly_connector.py",
    ]

    success = True
    for file_name in required_files:
        file_path = package_dir / file_name
        if file_path.exists():
            print(f"   ✅ {file_name}")
        else:
            print(f"   ❌ {file_name} missing")
            success = False

    return success


def check_dependencies():
    """Check if required dependencies are available."""
    print("\n🔍 Checking dependencies...")

    required_deps = ["metronome_pulse_core", "pydantic", "sqlite3"]  # Built-in

    success = True
    for dep in required_deps:
        try:
            if dep == "sqlite3":
                import sqlite3

                print(f"   ✅ {dep} (built-in)")
            else:
                importlib.import_module(dep)
                print(f"   ✅ {dep}")
        except ImportError as e:
            print(f"   ❌ {dep}: {e}")
            success = False

    return success


def check_version():
    """Check the package version."""
    print("\n🔍 Checking version...")

    try:
        from metronome_pulse_sqlite import __version__

        print(f"   ✅ Version: {__version__}")
        return True
    except ImportError as e:
        print(f"   ❌ Could not get version: {e}")
        return False


def main():
    """Main verification function."""
    print("🚀 DataPulse SQLite Connector - Setup Verification")
    print("=" * 60)

    checks = [
        ("Package Structure", check_package_structure),
        ("Dependencies", check_dependencies),
        ("Imports", check_imports),
        ("Classes", check_classes),
        ("Version", check_version),
    ]

    results = []

    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"   ❌ {check_name} check failed with error: {e}")
            results.append((check_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! The package is ready to use.")
        return 0
    else:
        print(f"\n💥 {total - passed} check(s) failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
