#!/usr/bin/env python3
"""
Demo Configuration Loader
Loads demo configurations into the podium system for demonstrations.
"""

import asyncio
import sys
from pathlib import Path

from datametronome_podium.services.stave_yaml_loader import (
    load_staves_from_yaml,
    validate_yaml_config,
)


async def load_demo_config(config_path: str, config_name: str):
    """Load a demo configuration and display results."""
    print(f"\n🎵 Loading {config_name}...")
    print("=" * 50)

    try:
        # Validate configuration first
        validation_result = validate_yaml_config(config_path)
        print(f"Validation: {'✅ VALID' if validation_result['valid'] else '❌ INVALID'}")

        if not validation_result["valid"]:
            print("Issues found:")
            for issue in validation_result["issues"]:
                print(f"  - {issue}")
            return False

        # Load the configuration
        staves, clefs = load_staves_from_yaml(config_path, resolve_env=False)

        print(f"✅ Loaded {len(staves)} staves and {len(clefs)} clefs")

        # Display staves
        print(f"\n📊 Staves:")
        for stave in staves:
            print(f"  - {stave}")

        # Display clefs grouped by level
        print(f"\n🎼 Clefs by Level:")
        level_1_clefs = [c for c in clefs if c.level == 1]
        level_2_clefs = [c for c in clefs if c.level == 2]
        level_3_clefs = [c for c in clefs if c.level == 3]
        level_4_clefs = [c for c in clefs if c.level == 4]

        if level_1_clefs:
            print(f"  Level 1 (Declarative): {len(level_1_clefs)} checks")
            for clef in level_1_clefs[:3]:  # Show first 3
                print(f"    - {clef}")
            if len(level_1_clefs) > 3:
                print(f"    ... and {len(level_1_clefs) - 3} more")

        if level_2_clefs:
            print(f"  Level 2 (Intelligent): {len(level_2_clefs)} checks")
            for clef in level_2_clefs:
                print(f"    - {clef}")

        if level_3_clefs:
            print(f"  Level 3 (Advanced): {len(level_3_clefs)} checks")
            for clef in level_3_clefs:
                print(f"    - {clef}")

        if level_4_clefs:
            print(f"  Level 4 (Custom): {len(level_4_clefs)} checks")
            for clef in level_4_clefs:
                print(f"    - {clef}")

        return True

    except Exception as e:
        print(f"❌ Error loading {config_name}: {e}")
        return False


async def main():
    """Main function to load demo configurations."""
    print("🎵 DataMetronome Demo Configuration Loader")
    print("=" * 50)

    # Get the examples directory
    examples_dir = Path(__file__).parent.parent / "examples"

    # Demo configurations to load
    demo_configs = [
        ("demo-clickstream.yaml", "Clickstream Monitoring"),
        ("demo-complete.yaml", "Comprehensive Demo"),
        ("tiered-checks-examples.yaml", "Tiered Checks Examples"),
    ]

    successful_loads = 0

    for config_file, config_name in demo_configs:
        config_path = examples_dir / config_file

        if config_path.exists():
            success = await load_demo_config(str(config_path), config_name)
            if success:
                successful_loads += 1
        else:
            print(f"❌ Configuration file not found: {config_path}")

    print(f"\n🎉 Demo Configuration Summary")
    print("=" * 30)
    print(
        f"✅ Successfully loaded: {successful_loads}/{len(demo_configs)} configurations"
    )

    if successful_loads > 0:
        print(f"\n📋 Next Steps:")
        print(f"  1. Use the UI to visualize these configurations")
        print(f"  2. Run the import script to load into your database:")
        print(
            f"     python -m datametronome_podium.scripts.import_staves examples/demo-simple-monitoring.yaml"
        )
        print(f"  3. Test the configurations with your demo environment")


if __name__ == "__main__":
    asyncio.run(main())
