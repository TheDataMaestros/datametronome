#!/usr/bin/env python3
"""
Import staves from YAML configuration files.

Usage:
    python scripts/import_staves.py staves.yaml
    python scripts/import_staves.py production-db.yaml --overwrite
    python scripts/import_staves.py staves.yaml --validate-only
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import datametronome_podium
sys.path.insert(0, str(Path(__file__).parent.parent))

from datametronome_podium.core.database import get_db
from datametronome_podium.services.stave_yaml_loader import (
    import_staves_from_yaml,
    validate_yaml_config
)


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Import staves and clefs from YAML configuration"
    )
    parser.add_argument(
        "yaml_file",
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing staves/clefs with same ID"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the YAML file, don't import"
    )
    parser.add_argument(
        "--no-env",
        action="store_true",
        help="Don't resolve environment variables"
    )
    
    args = parser.parse_args()
    
    yaml_path = Path(args.yaml_file)
    
    if not yaml_path.exists():
        print(f"❌ Error: File not found: {yaml_path}")
        sys.exit(1)
    
    print(f"📋 Loading configuration from: {yaml_path}")
    print()
    
    # Validate with comprehensive conflict detection
    print("🔍 Validating configuration for conflicts and dissonance...")
    result = validate_yaml_config(yaml_path)
    
    print(result["summary"])
    
    # Show issues grouped by severity
    errors = [i for i in result["issues"] if i.severity == "error"]
    warnings = [i for i in result["issues"] if i.severity == "warning"]
    info = [i for i in result["issues"] if i.severity == "info"]
    
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for error in errors:
            print(f"   {error}")
    
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"   {warning}")
    
    if info:
        print(f"\nℹ️  Info ({len(info)}):")
        for info_item in info:
            print(f"   {info_item}")
    
    # Show recommendations
    if result["recommendations"]:
        print(f"\n💡 Recommendations:")
        for rec in result["recommendations"]:
            print(f"   - {rec}")
    
    if errors:
        print(f"\n❌ Configuration has {len(errors)} error(s). Fix these before importing.")
        sys.exit(1)
    
    if args.validate_only:
        print("\n✅ Validation complete!")
        sys.exit(0)
    
    # Import
    print("\n📥 Importing to database...")
    db = await get_db()
    
    try:
        counts = await import_staves_from_yaml(
            yaml_path,
            db,
            resolve_env=not args.no_env,
            overwrite=args.overwrite
        )
        
        print()
        print("=" * 50)
        print(f"✅ Import complete!")
        print(f"   Staves imported: {counts['staves']}")
        print(f"   Clefs imported:  {counts['clefs']}")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

