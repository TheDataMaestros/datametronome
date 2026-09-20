#!/usr/bin/env python
"""POST a sample alert to a Slack webhook, using the real payload builder.

The point is that this sends exactly what a failing check sends -- if it looks
right in Slack, alerting looks right in Slack. Nothing is mocked but the check.

    python scripts/send_test_alert.py --webhook-file /path/to/webhook.txt
    python scripts/send_test_alert.py --webhook-file … --kind recovered

The URL is read from a file rather than an argument so it stays out of shell
history and `ps`. Pass --dry-run to print the payload and send nothing.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from datametronome_podium.services.alerting import build_payload  # noqa: E402

# Values are heterogeneous (str and bool), so they widen to a union when
# unpacked; Any keeps the type checker out of the sample table.
SAMPLES: dict[str, dict[str, Any]] = {
    "fail": dict(
        clef_name="Email NULL Check",
        status="fail",
        severity="cacophony",
        message="NULL rate 7.20% violates fail condition (if_null > 5%)",
        recovered=False,
    ),
    "warn": dict(
        clef_name="Daily Order Volume",
        status="warn",
        severity="dissonance",
        message="Row count 412 breaches warning condition (< 500)",
        recovered=False,
    ),
    "recovered": dict(
        clef_name="Email NULL Check",
        status="pass",
        severity="harmony",
        message="NULL rate 0.10% within acceptable limits",
        recovered=True,
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--webhook-file", type=pathlib.Path,
                    help="File containing the Slack webhook URL on one line")
    ap.add_argument("--kind", choices=sorted(SAMPLES), default="fail")
    ap.add_argument("--base-url", default="https://datametronome.example.com",
                    help="Podium base URL, for the 'View check' link")
    ap.add_argument("--dry-run", action="store_true", help="Print, do not send")
    args = ap.parse_args()

    sample = SAMPLES[args.kind]
    payload = build_payload(
        check_id="check-demo-1",
        clef_id="clef-demo-1",
        stave_id="stave-demo-1",
        stave_name="prod-warehouse",
        base_url=args.base_url,
        **sample,
    )

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    if not args.webhook_file:
        ap.error("--webhook-file is required unless --dry-run")
    url = args.webhook_file.read_text().strip()
    if not url.startswith("https://hooks.slack.com/"):
        print(f"Refusing to post: {url[:40]!r} is not a Slack webhook URL", file=sys.stderr)
        return 2

    response = httpx.post(url, json=payload, timeout=10.0)
    print(f"{response.status_code} {response.text}")
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
