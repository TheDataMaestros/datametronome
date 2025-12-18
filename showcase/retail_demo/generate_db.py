#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Generate the Retail demo SQLite database.")
    p.add_argument(
        "--out",
        default="datametronome/podium/data/retail.db",
        help="Output SQLite DB path (relative to repo root by default).",
    )
    return p.parse_args()


def main():
    args = parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (project_root / out_path).resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)

    from showcase.retail_demo.generate_data import create_retail_db

    print(f"Generating Retail demo DB at: {out_path}")
    create_retail_db(str(out_path))


if __name__ == "__main__":
    main()


