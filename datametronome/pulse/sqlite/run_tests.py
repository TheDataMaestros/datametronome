#!/usr/bin/env python3
"""
Simple test runner for DataPulse SQLite connector.

This script provides a convenient way to run tests during development.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run DataPulse SQLite tests")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "slow", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Run tests with coverage"
    )
    parser.add_argument(
        "--lint", 
        action="store_true",
        help="Run linting checks"
    )
    parser.add_argument(
        "--format", 
        action="store_true",
        help="Format code"
    )
    
    args = parser.parse_args()
    
    # Change to the package directory
    package_dir = Path(__file__).parent
    os.chdir(package_dir)
    
    success = True
    
    # Run linting if requested
    if args.lint:
        success &= run_command(
            ["make", "lint"], 
            "Code linting and formatting checks"
        )
    
    # Format code if requested
    if args.format:
        success &= run_command(
            ["make", "format"], 
            "Code formatting"
        )
    
    # Run tests based on type
    if args.type == "unit":
        success &= run_command(
            ["make", "test-unit"], 
            "Unit tests"
        )
    elif args.type == "integration":
        success &= run_command(
            ["make", "test-integration"], 
            "Integration tests"
        )
    elif args.type == "slow":
        success &= run_command(
            ["make", "test-slow"], 
            "Slow/performance tests"
        )
    else:  # all
        if args.coverage:
            success &= run_command(
                ["make", "test-cov"], 
                "All tests with coverage"
            )
        else:
            success &= run_command(
                ["make", "test"], 
                "All tests"
            )
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All operations completed successfully!")
        sys.exit(0)
    else:
        print("💥 Some operations failed. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()
